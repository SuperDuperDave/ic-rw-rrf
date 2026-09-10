"""Synthetic observation/censoring fixtures only; no research data evaluation.

Run: python3 -B -m unittest discover -s evaluation/tests -p test_cycle02_observation_audit.py -v
"""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from evaluation import cycle02_observation_audit as audit


NEW = 'new-source'


def independent_lists(depth=40):
    return {name: ['{}-{}'.format(name, rank) for rank in range(1, depth + 1)]
            for name in (*audit.LEXICAL, NEW)}


def run_text(query, documents, origin):
    return ''.join('{} Q0 {} {} {} fixture\n'.format(query, doc, rank + origin, len(documents) - rank)
                   for rank, doc in enumerate(documents))


class ObservationTests(unittest.TestCase):
    def test_third_source_top30_veto_overrules_other_source_tail_support(self):
        lists = {'owner': ['special'],
                 'tail': ['f{}'.format(i) for i in range(30)] + ['special'],
                 'veto': ['special']}
        candidates = audit.specialist_candidates(lists, lists, {'special'})
        self.assertNotIn('special', [row['docid'] for row in candidates])
        lists['veto'] = []
        candidates = audit.specialist_candidates(lists, lists, {'special'})
        special = next(row for row in candidates if row['docid'] == 'special')
        self.assertEqual(special['group'], 'tail_supported')
        self.assertEqual(special['full_source_ranks'], {'owner': 1, 'tail': 31, 'veto': None})

    def test_zero_grade_is_judged_and_missing_is_not_filled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'qrels.txt'
            path.write_text('q Q0 zero 0\nq Q0 positive 3\n', encoding='utf-8')
            judged = audit.read_judged_membership(path)['q']
        self.assertEqual(judged, {'zero', 'positive'})
        stats = audit.counts(['zero', 'positive', 'missing'], judged)
        self.assertEqual(stats['n_judged'], 2)
        self.assertEqual(stats['n_unjudged'], 1)
        self.assertEqual(stats['judged_fraction'], 2 / 3)
        self.assertIsNone(audit.counts([], judged)['judged_fraction'])
        candidates = audit.specialist_candidates({'a': ['zero', 'missing']}, {'a': ['zero', 'missing']}, judged)
        self.assertEqual([row['judged'] for row in candidates], [True, False])
        self.assertFalse(any('grade' in key or 'gain' in key for row in candidates for key in row))

    def test_candidate_newness_is_not_top30_disagreement(self):
        lists = independent_lists()
        lists[NEW][0:2] = ['lexical-tail', 'actually-new']
        lists['bm25'][30] = 'lexical-tail'
        result = audit.inspect_query(lists, NEW, {'lexical-tail', 'actually-new'})
        full = result['arms']['full']
        candidates = {row['docid']: row for row in full['specialist_candidates']}
        self.assertEqual(candidates['lexical-tail']['group'], 'tail_supported')
        outside = full['new_source_top10_outside_lexical_full_union']
        self.assertNotIn('lexical-tail', [row['docid'] for row in outside['documents']])
        self.assertIn('actually-new', [row['docid'] for row in outside['documents']])
        self.assertEqual(outside['counts']['n_judged'], 1)
        self.assertEqual(full['pairwise_source_overlap']['bm25'][NEW]['n_intersection'], 1)

    def test_shared_depth_crops_every_source_and_preserves_input(self):
        lists = {name: ['{}-{}'.format(name, i) for i in range(depth)]
                 for name, depth in zip((*audit.LEXICAL, NEW), (201, 240, 230, 222, 1001))}
        result = audit.inspect_query(lists, NEW, set())
        self.assertEqual(result['shared_depth'], 200)
        self.assertEqual(set(result['changed_sources']), set(lists))
        self.assertTrue(all(depth == 200 for depth in result['arms']['shared_depth']['source_depths'].values()))
        self.assertEqual(result['arms']['full']['source_depths'][NEW], 1000)
        self.assertEqual(result['raw_source_depths'][NEW], 1001)
        self.assertEqual(len(lists[NEW]), 1001)
        coverage = result['new_source_full_vs_capped_outside_candidate_coverage']
        self.assertEqual([coverage[key]['n_candidates'] for key in ('full', 'capped', 'removed_by_cap')],
                         [1000, 200, 800])
        self.assertTrue(result['arms']['shared_depth']['candidate_set_changed_from_full'])
        # An arm that makes no change must be recorded as such.
        noop = audit.inspect_query(independent_lists(40), NEW, set())
        self.assertFalse(noop['depth_arm_changed'])
        self.assertFalse(noop['arms']['shared_depth']['candidate_set_changed_from_full'])

    def test_cropping_never_invents_specialists_or_relabels_tail_as_isolated(self):
        lists = independent_lists()
        lists['tfidf'] = lists['tfidf'][:5]
        lists[NEW][0:2] = ['vetoed', 'supported']
        lists[NEW][6] = 'censored-owner'
        lists['bm25'][9] = 'vetoed'
        lists['bm25'][30] = 'supported'
        result = audit.inspect_query(lists, NEW, {'supported', 'censored-owner'})
        self.assertEqual(result['shared_depth'], 5)
        cohorts = [{row['docid']: row for row in result['arms'][arm]['specialist_candidates']} for arm in audit.ARMS]
        self.assertEqual(set(cohorts[0]), set(cohorts[1]))
        self.assertNotIn('vetoed', cohorts[1])
        capped = cohorts[1]
        self.assertEqual(capped['supported']['group'], 'tail_supported')
        self.assertEqual(capped['supported']['full_source_ranks']['bm25'], 31)
        self.assertIsNone(capped['supported']['source_ranks']['bm25'])
        self.assertEqual(capped['supported']['full_tail_support_sources'], ['bm25'])
        self.assertEqual(capped['supported']['active_tail_support_sources'], [])
        self.assertFalse(capped['censored-owner']['owner_visible'])
        fixed = audit.owner_summaries({'q': result}, 'shared_depth', NEW)['new_source']
        visible = audit.owner_summaries({'q': result}, 'shared_depth', NEW, visible_only=True)['new_source']
        self.assertGreater(fixed['groups']['isolated']['n_candidates'], visible['groups']['isolated']['n_candidates'])
        self.assertEqual(fixed['groups']['isolated']['n_judged'], 1)
        self.assertEqual(visible['groups']['isolated']['n_judged'], 0)
        # Losing lexical evidence creates apparent newness only in the active-union view.
        self.assertEqual(result['arms']['shared_depth']['new_source_outside_only_due_to_lexical_cropping']['n_candidates'], 2)

    def test_sparse_paired_eligibility_does_not_pool_documents_into_queries(self):
        tail = {'group': 'tail_supported', 'judged': True}
        isolated = {'group': 'isolated', 'judged': True}
        unjudged = {'group': 'isolated', 'judged': False}
        summary = audit.summarize_groups({'both': [tail, isolated], 'partial': [tail, unjudged],
                                         'single': [isolated] * 20, 'empty': []})
        eligible = summary['eligibility']
        self.assertEqual(eligible['with_candidates']['n_queries'], 3)
        self.assertEqual(eligible['with_both_groups']['qids'], ['both', 'partial'])
        self.assertEqual(eligible['with_judged_both_groups']['qids'], ['both'])
        self.assertEqual(summary['per_query_denominators']['partial']['isolated']['n_judged'], 0)
        self.assertIsNone(summary['per_query_denominators']['empty']['isolated']['judged_fraction'])
        censored = audit.summarize_groups({'both': [tail], 'partial': [tail, unjudged], 'single': [], 'empty': []})
        paired = audit.paired_observability(summary, censored)
        self.assertEqual(paired['with_both_groups']['qids'], ['partial'])
        self.assertEqual(paired['with_judged_both_groups']['n_queries'], 0)

    def test_query_omissions_are_explicit_and_do_not_select_by_judgments(self):
        lists = independent_lists(2)
        runs = {name: {'q1': docs, 'q2': docs, 'extra': docs} for name, docs in lists.items()}
        del runs[NEW]['q2']
        summary, rows = audit.summarize_year(2019, NEW, runs, {'q1': set(), 'q2': {'known'}})
        self.assertEqual(summary['eligible_qids'], ['q1'])
        self.assertEqual(summary['excluded_qrel_queries'], {'q2': {'missing_sources': [NEW]}})
        self.assertEqual(summary['raw_input_inventory'][NEW]['qids_without_qrels'], ['extra'])
        self.assertEqual(summary['raw_input_inventory'][NEW]['qids_missing_from_source'], ['q2'])
        self.assertEqual(rows['q1']['arms']['full']['candidate_union']['n_judged'], 0)
        self.assertEqual(summary['n_queries_depth_arm_changed'], 0)


class InputValidationTests(unittest.TestCase):
    def test_rank_origin_and_serialized_ties_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.txt'
            path.write_text('q Q0 z 0 1 tag\nq Q0 a 1 1 tag\n', encoding='utf-8')
            self.assertEqual(audit.read_ranked_run(path, 0), {'q': ['z', 'a']})
            with self.assertRaisesRegex(ValueError, 'origin 1'):
                audit.read_ranked_run(path, 1)
            path.write_text('q Q0 z 1 1 tag\nq Q0 a 2 1 tag\n', encoding='utf-8')
            self.assertEqual(audit.read_ranked_run(path, 1), {'q': ['z', 'a']})

    def test_malformed_duplicate_nonfinite_and_increasing_runs_fail_closed(self):
        bad = {
            'malformed': 'q Q0 doc 1 1\n',
            'duplicate': 'q Q0 a 1 2 t\nq Q0 a 2 1 t\n',
            'nonfinite': 'q Q0 a 1 nan t\n',
            'score increase': 'q Q0 a 1 1 t\nq Q0 b 2 2 t\n',
            'rank gap': 'q Q0 a 1 2 t\nq Q0 b 3 1 t\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run.txt'
            for label, content in bad.items():
                with self.subTest(label=label):
                    path.write_text(content, encoding='utf-8')
                    with self.assertRaises(ValueError):
                        audit.read_ranked_run(path, 1)

    def test_manifest_requires_identity_two_years_relative_paths_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = []
            for year in audit.YEARS:
                path = root / '{}.txt'.format(year)
                path.write_text(run_text('q', ['d'], 1), encoding='utf-8')
                entries.append({'year': year, 'path': path.name, 'sha256': audit.sha256(path)})
            manifest_path = root / 'source.json'
            good = {'source_id': NEW, 'derived_runs': entries, 'ignored_provenance': {'x': True}}
            manifest_path.write_text(json.dumps(good), encoding='utf-8')
            name, loaded = audit.load_source_manifest(manifest_path, root)
            self.assertEqual(name, NEW)
            self.assertEqual(set(loaded), set(audit.YEARS))
            cases = [[], dict(good, source_id='bm25'), dict(good, derived_runs=entries[:1]),
                     dict(good, derived_runs=[entries[0], entries[0]]),
                     dict(good, derived_runs=[dict(entries[0], year=True), entries[1]]),
                     dict(good, derived_runs=[dict(entries[0], path=str(root / '2019.txt')), entries[1]]),
                     dict(good, derived_runs=[dict(entries[0], sha256='0' * 64), entries[1]]),
                     dict(good, derived_runs=[dict(entries[0], sha256='bad'), entries[1]]),
                     dict(good, derived_runs=[dict(entries[0], path='../escape.txt'), entries[1]])]
            for invalid in cases:
                with self.subTest(manifest=invalid):
                    manifest_path.write_text(json.dumps(invalid), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        audit.load_source_manifest(manifest_path, root)


class ArtifactTests(unittest.TestCase):
    def fixture_repository(self, root):
        script = root / 'evaluation' / 'cycle02_observation_audit.py'
        script.parent.mkdir()
        script.write_text('fixture script identity\n', encoding='utf-8')
        protocol = root / 'protocol.md'
        protocol.write_text('Frozen synthetic protocol\n', encoding='utf-8')
        acquired = root / 'data' / 'cycle02' / 'acquired'
        acquired.mkdir(parents=True)
        (acquired.parent / 'source-selection.json').write_text('{"selection":"fixture"}\n', encoding='utf-8')
        derived = []
        for year in audit.YEARS:
            directory = root / 'data' / ('trec-dl-' + str(year))
            (directory / 'runs').mkdir(parents=True)
            (directory / '{}qrels-pass.txt'.format(year)).write_text('q Q0 zero 0\nq Q0 present 2\n', encoding='utf-8')
            for name in audit.LEXICAL:
                (directory / 'runs' / (name + '.txt')).write_text(run_text('q', ['zero', 'unknown'], 0), encoding='utf-8')
            source = acquired / '{}.txt'.format(year)
            source.write_text(run_text('q', ['present', 'unjudged-new'], 1), encoding='utf-8')
            derived.append({'year': year, 'path': str(source.relative_to(root)), 'sha256': audit.sha256(source)})
        manifest = acquired / 'source-manifest.json'
        manifest.write_text(json.dumps({'source_id': NEW, 'derived_runs': derived}), encoding='utf-8')
        return script, protocol, manifest

    def test_synthetic_cli_writes_verified_artifacts_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, protocol, manifest = self.fixture_repository(root)
            output = root / 'result'
            argv = ['--source-manifest', str(manifest), '--protocol', str(protocol), '--output', str(output)]
            with mock.patch.object(audit, 'ROOT', root), mock.patch.object(audit, '__file__', str(script)), \
                    mock.patch.object(audit.subprocess, 'check_output', side_effect=['fixture-head\n', ' M fixture\n']), \
                    contextlib.redirect_stdout(io.StringIO()):
                audit.main(argv)
                with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                    audit.main(argv)
            receipt = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['status'], 'complete')
            self.assertTrue(receipt['sources_and_inputs_unchanged'])
            self.assertEqual(receipt['source_sha256_start'], receipt['source_sha256_end'])
            self.assertEqual(receipt['input_sha256_start'], receipt['input_sha256_end'])
            self.assertEqual(receipt['argv'], [str(script)] + argv)
            self.assertEqual(len(receipt['input_sha256_start']), 12)
            self.assertEqual(len(receipt['source_sha256_start']), 4)
            for name, digest in receipt['output_sha256'].items():
                self.assertEqual(audit.sha256(output / name), digest)
            observations = json.loads((output / 'per_query.json').read_text(encoding='utf-8'))
            full = observations['2019']['q']['arms']['full']
            self.assertEqual(full['source_judgment_coverage']['bm25']['whole_source']['n_judged'], 1)
            self.assertEqual(full['new_source_top10_outside_lexical_full_union']['counts']['n_unjudged'], 1)
            self.assertFalse((output / 'manifest-invalid.json').exists())

    def test_input_change_during_run_invalidates_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, protocol, manifest = self.fixture_repository(root)
            output = root / 'result'
            original = audit.summarize_year

            def mutate_after_observation(*args):
                result = original(*args)
                if args[0] == 2020:
                    protocol.write_text('Changed protocol\n', encoding='utf-8')
                return result

            with mock.patch.object(audit, 'ROOT', root), mock.patch.object(audit, '__file__', str(script)), \
                    mock.patch.object(audit.subprocess, 'check_output', side_effect=['fixture-head\n', '']), \
                    mock.patch.object(audit, 'summarize_year', side_effect=mutate_after_observation):
                with self.assertRaisesRegex(RuntimeError, 'changed during'):
                    audit.main(['--source-manifest', str(manifest), '--protocol', str(protocol), '--output', str(output)])
            self.assertTrue((output / 'manifest-invalid.json').exists())
            self.assertFalse((output / 'manifest.json').exists())
            self.assertFalse((output / 'summary.json').exists())

    def test_bad_lexical_contract_keeps_hash_receipt_without_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script, protocol, manifest = self.fixture_repository(root)
            lexical = root / 'data' / 'trec-dl-2019' / 'runs' / 'bm25.txt'
            lexical.write_text('q Q0 doc 1 1 fixture\n', encoding='utf-8')
            output = root / 'result'
            with mock.patch.object(audit, 'ROOT', root), mock.patch.object(audit, '__file__', str(script)), \
                    mock.patch.object(audit.subprocess, 'check_output', side_effect=['fixture-head\n', '']):
                with self.assertRaisesRegex(ValueError, 'origin 0'):
                    audit.main(['--source-manifest', str(manifest), '--protocol', str(protocol), '--output', str(output)])
            receipt = json.loads((output / 'manifest-invalid.json').read_text(encoding='utf-8'))
            self.assertEqual(receipt['status'], 'invalid')
            self.assertTrue(receipt['sources_and_inputs_unchanged'])
            self.assertEqual(len(receipt['input_sha256_end']), 12)
            self.assertFalse((output / 'summary.json').exists())


if __name__ == '__main__':
    unittest.main()
