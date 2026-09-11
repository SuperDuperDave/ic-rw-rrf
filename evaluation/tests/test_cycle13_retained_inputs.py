"""Synthetic-only checks for the retained-input correction boundary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation import cycle13_retained_inputs as audit


def synthetic_inputs(root):
    """Use the full prescribed cohort sizes, with deliberately different depths."""
    inventory = {'preserve_full_retained_lists': True, 'years': {}}
    expected_runs = {}
    for year in audit.frozen.YEARS:
        directory = root / 'data' / ('trec-dl-' + str(year))
        directory.mkdir(parents=True)
        (directory / (str(year) + 'qrels-pass.txt')).write_text('q00 0 d00 0\n')
        runs, entries = {}, {}
        for source_index, name in enumerate(audit.frozen.SOURCES):
            lexical = name in audit.frozen.LEXICAL
            relative = (Path('data') / ('trec-dl-' + str(year)) / 'runs' / (name + '.txt')
                        if lexical else Path('data/cycle02/acquired') / ('dl' + str(year) + '.trec'))
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            rows, runs[name] = [], {}
            for index in range(audit.frozen.EXPECTED_QUERY_COUNTS[year]):
                qid = 'q{:02d}'.format(index)
                depth = (2 if index == 0 else (3, 11, 17)[(index + source_index) % 3]) if lexical else 7 + index % 2 * 12
                docs = ['d{:02d}'.format(i) for i in range(depth)]
                if source_index % 2:
                    docs.reverse()
                runs[name][qid] = docs
                rows.extend('{} Q0 {} {} {} synthetic\n'.format(qid, doc, rank + (not lexical), 100 - rank)
                            for rank, doc in enumerate(docs))
            path.write_text(''.join(rows))
            entries[name] = {'path': str(relative)}
        for name, depths in audit.source_depths(runs).items():
            entries[name].update(depths)
        inventory['years'][str(year)] = entries
        expected_runs[year] = runs
    inventory['input_sha256'] = audit.frozen._input_hashes(audit.frozen.fixed_inputs(root), root)
    path = root / audit.INVENTORY
    path.parent.mkdir(parents=True)
    path.write_text(audit.canonical_json(inventory))
    return inventory, expected_runs


class RetainedInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inventory, self.runs = synthetic_inputs(self.root)
        self.output = self.root / 'output'

    def test_each_input_identity_checked_before_parsing_or_scoring(self):
        for relative in self.inventory['input_sha256']:
            with self.subTest(input=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                try:
                    with patch.object(audit.frozen, 'read_ranked_run') as reader, \
                            patch.object(audit.frozen, 'read_qrels') as qrels, \
                            patch.object(audit, 'canonical_rrf') as fusion, \
                            patch.object(audit, 'analyze_query') as scorer:
                        with self.assertRaisesRegex(ValueError, 'hash identity'):
                            audit.run_audit(self.output, self.root)
                        for function in (reader, qrels, fusion, scorer):
                            function.assert_not_called()
                    self.assertFalse(self.output.exists())
                finally:
                    path.write_bytes(original)

    def test_later_year_depth_failure_precedes_all_qrels_and_scoring(self):
        entry = self.inventory['years']['2020']['bm25']
        entry['query_depths']['q00'] += 1
        (self.root / audit.INVENTORY).write_text(audit.canonical_json(self.inventory))
        with patch.object(audit.frozen, 'read_qrels') as qrels, \
                patch.object(audit, 'canonical_rrf') as fusion, \
                patch.object(audit, 'analyze_query') as scorer:
            with self.assertRaisesRegex(ValueError, 'exact retained depth'):
                audit.run_audit(self.output, self.root)
            for function in (qrels, fusion, scorer):
                function.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_exact_variable_lists_reach_fusion_and_outputs_pin_custody(self):
        with patch.object(audit, 'canonical_rrf', wraps=audit.canonical_rrf) as fusion:
            records, summary, manifest = audit.run_audit(self.output, self.root, ['synthetic'])
        expected_calls = []
        for year in audit.frozen.YEARS:
            runs = self.runs[year]
            qids = sorted(runs['bm25'])
            self.assertEqual(list(records[str(year)]), qids)
            self.assertEqual(summary['years'][str(year)]['source_depths'], audit.source_depths(runs))
            self.assertEqual(len(records[str(year)]['q00']['top10_a']), 2)
            for qid in qids:
                lexical = [runs[name][qid] for name in audit.frozen.LEXICAL]
                expected_calls.extend([lexical, lexical + [runs[audit.frozen.SOURCE_ID][qid]]])
        self.assertEqual([call.args[0] for call in fusion.call_args_list], expected_calls)
        self.assertEqual(fusion.call_count, 194)
        self.assertTrue(all(call.kwargs == {'k': 60} for call in fusion.call_args_list))
        self.assertEqual(set(p.name for p in self.output.iterdir()), {'per_query.json', 'summary.json', 'manifest.json'})
        self.assertEqual(manifest['source_sha256_start'], manifest['source_sha256_end'])
        self.assertEqual(set(manifest['source_sha256_start']), set(audit.SOURCE_FILES))
        self.assertEqual(len(manifest['source_sha256_start']), 10)
        self.assertEqual(manifest['input_sha256_start'], self.inventory['input_sha256'])
        self.assertEqual(manifest['input_sha256_start'], manifest['input_sha256_end'])
        for filename, digest in manifest['artifact_sha256'].items():
            self.assertEqual(audit.frozen.sha256(self.output / filename), digest)
        for path in self.output.iterdir():
            self.assertEqual(path.read_text(), audit.canonical_json(json.loads(path.read_text())))
        with patch.object(audit.frozen, 'fixed_inputs') as reader:
            with self.assertRaises(FileExistsError):
                audit.run_audit(self.output, self.root)
            reader.assert_not_called()

    def test_inventory_path_and_typed_depths_are_not_repaired(self):
        malformed = copy.deepcopy(self.inventory)
        malformed['years']['2019']['bm25']['path'] = 'somewhere/else.txt'
        with patch.object(audit.frozen, 'read_ranked_run') as reader:
            with self.assertRaisesRegex(ValueError, 'source path'):
                audit.load_validated_inputs(self.root, malformed)
            reader.assert_not_called()
        entries = copy.deepcopy(self.inventory['years']['2019'])
        entries['bm25']['query_depths']['q00'] = True
        with self.assertRaisesRegex(ValueError, 'inventory depths'):
            audit.validate_retained_runs(self.runs[2019], entries, 43)
        entries = copy.deepcopy(self.inventory['years']['2019'])
        entries['bm25']['depth_histogram']['2'] += 1
        with self.assertRaisesRegex(ValueError, 'exact retained depth'):
            audit.validate_retained_runs(self.runs[2019], entries, 43)

    def test_missing_query_and_duplicate_document_are_not_repaired(self):
        runs = copy.deepcopy(self.runs[2019])
        del runs['bm25']['q00']
        with self.assertRaisesRegex(ValueError, 'complete prescribed cohort'):
            audit.validate_retained_runs(runs, self.inventory['years']['2019'], 43)
        runs = copy.deepcopy(self.runs[2019])
        runs['bm25']['q00'][1] = runs['bm25']['q00'][0]
        with self.assertRaises(ValueError):
            audit.validate_retained_runs(runs, self.inventory['years']['2019'], 43)


if __name__ == '__main__':
    unittest.main()
