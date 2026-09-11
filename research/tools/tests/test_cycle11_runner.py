"""Cycle11 atomic responses and native controls, using a synthetic parent only."""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1]
# Reuse only frozen fake streams and temporary-file harnesses, never prior setup.
spec = importlib.util.spec_from_file_location('cycle11_test_helpers', TOOLS / 'tests/test_cycle09_runner.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
with mock.patch.dict(sys.modules, {'run_cycle05_coordinator': prior.shared, 'native_stream_observer': prior.native}):
    runner = prior.load('cycle11_runner_under_test', TOOLS / 'run_cycle11_verifier.py')
scorer = prior.load('cycle11_scorer_under_test', TOOLS / 'score_cycle11_verifier.py')
from evaluation import cycle10_certificates as parent_packets


class Cycle11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(parent_packets, 'build_fixture', side_effect=AssertionError('actual panel forbidden')) as actual, \
                mock.patch.object(parent_packets.previous.random, 'Random', side_effect=AssertionError('RNG forbidden')) as draw:
            parent = parent_packets.construct_fixture(-3, 4)
            cls.local_fixture = runner.packets.construct_fixture(parent)
            actual.assert_not_called()
            draw.assert_not_called()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'synthetic-source.txt'
        self.source.write_text('immutable synthetic source')
        self.fixture = deepcopy(self.local_fixture)
        self.fixture.update(system_prompt=runner.measure.SYSTEM_PROMPT,
            system_prompt_sha256=hashlib.sha256(runner.measure.SYSTEM_PROMPT.encode()).hexdigest(),
            request_order=list(runner.measure.ORDER), prepared_manifest_sha256='synthetic-prepared')
        self.packets = {p['packet_id']: p for p in self.fixture['packets']}
        self.programs = {p['program_id']: p for p in self.fixture['programs']}
        self.payloads = {pid: json.loads(p['payload']) for pid, p in self.packets.items()}
        self.ids = {pid: p['submission_ids'] for pid, p in self.payloads.items()}
        self.false_responses = {pid: {'answer': False, 'validity': dict.fromkeys(ids, False)}
                                for pid, ids in self.ids.items()}
        self.exact = {}
        for pid, packet in self.packets.items():
            program = self.programs[packet['program_id']]
            self.exact[pid] = {'answer': program['python_truth']['answer'], 'validity': {
                report['report_id']: label == 'V'
                for label, report in zip(packet['private_order'], self.payloads[pid]['reports'][:4])}}

    def collect(self, **options):
        options.setdefault('terminals', [json.dumps(self.false_responses[pid]) for pid in runner.measure.ORDER])
        options.setdefault('costs', [.01] * 4)
        with mock.patch.object(prior, 'runner', runner):
            return prior.CollectionTests.collect(self, **options)

    def score(self, output):
        with mock.patch.object(prior, 'scorer', scorer):
            return prior.CollectionTests.score(self, output)

    @contextmanager
    def execution_context(self):
        with mock.patch.object(prior, 'runner', runner):
            with prior.CollectionTests.execution_context(self) as execution:
                yield execution

    def test_strict_atomic_schema_rejects_old_maps_duplicates_and_nonbooleans(self):
        pid = runner.measure.ORDER[0]
        response = self.false_responses[pid]
        good = json.dumps(response)
        invalid = [json.dumps(response['validity']), 'false', '[]', 'null', '{}',
                   good + good, 'Answer: ' + good, '```json\n' + good + '\n```',
                   good[:-1] + ',"answer":true}',
                   good.replace('"answer": false', '"answer": NaN'),
                   good.replace('"answer": false', '"answer": ' + '9' * 5000),
                   json.dumps({'answer': False, 'validity': response['validity'], 'extra': False})]
        for field in ('answer', 'validity'):
            bad = deepcopy(response)
            del bad[field]
            invalid.append(json.dumps(bad))
        for value in (0, 1, None, 'false', [], {}):
            invalid.append(json.dumps(dict(response, answer=value)))
            bad = deepcopy(response)
            bad['validity'][self.ids[pid][0]] = value
            invalid.append(json.dumps(bad))
        for change in ('missing', 'extra', 'wrong-case'):
            bad = deepcopy(response)
            key = self.ids[pid][0]
            if change == 'missing':
                del bad['validity'][key]
            elif change == 'extra':
                bad['validity']['s_extra'] = False
            else:
                bad['validity'][key.upper()] = bad['validity'].pop(key)
            invalid.append(json.dumps(bad))
        duplicate_map = json.dumps(response['validity'])[:-1] + ',' + json.dumps(self.ids[pid][0]) + ':true}'
        invalid.append('{"answer":false,"validity":' + duplicate_map + '}')
        for terminal in invalid:
            with self.subTest(terminal=terminal[:120]):
                with self.assertRaises(runner.measure.MapParseError):
                    runner.measure.parse_response(terminal, self.ids[pid])
                frames = prior.events(terminal)
                frames[1]['message']['content'][0]['text'] = good
                record = runner.inspect_stream(prior.encode(frames), 0, prior.SESSION, self.ids[pid])
                self.assertTrue(record['native_acceptable'])
                self.assertIsNone(record['response'])
                self.assertIsNotNone(record['parse_failure'])
        frames = prior.events(' \n' + good + '\t ')
        frames[1]['message']['content'][0]['text'] = 'not the terminal answer'
        record = runner.inspect_stream(prior.encode(frames), 0, prior.SESSION, self.ids[pid])
        self.assertEqual(record['response'], response)
        self.assertIsNone(record['parse_failure'])
        self.assertNotIn('SYNTHETIC_PRIVATE_SENTINEL', json.dumps(record))
        for obsolete in ('answer', 'validity', 'p_positive'):
            self.assertNotIn(obsolete, record)

    def test_native_refusal_tools_and_timeout_prevent_atomic_parsing(self):
        pid = runner.measure.ORDER[0]
        for name in ('refusal', 'tool', 'timeout'):
            frames = prior.events(json.dumps(self.exact[pid]))
            if name == 'refusal':
                frames[-1].update(is_error=True, subtype='error_during_execution', stop_reason='refusal')
                frames.insert(1, {'type': 'system', 'subtype': 'model_refusal_no_fallback',
                    'session_id': prior.SESSION, 'request_id': 'synthetic-request',
                    'original_model': runner.MODEL, 'api_refusal_category': 'reasoning_extraction'})
            elif name == 'tool':
                frames[1]['message']['content'].append({'type': 'tool_use', 'name': 'Read'})
            with self.subTest(name=name), mock.patch.object(runner.measure, 'parse_response') as parse:
                record = runner.inspect_stream(prior.encode(frames), 0, prior.SESSION, self.ids[pid], name == 'timeout')
                parse.assert_not_called()
                self.assertFalse(record['native_acceptable'])
                self.assertIsNone(record['response'])
                self.assertIsNone(record['parse_failure'])
                self.assertIn({'refusal': 'provider_refusal', 'tool': 'tool_activity', 'timeout': 'timeout'}[name], record['issues'])

    def test_four_calls_accept_false_answer_and_false_validity_without_early_stop(self):
        self.assertEqual(tuple(runner.measure.ORDER), ('R0-A', 'R1-B', 'R0-B', 'R1-A'))
        for name in ('command', 'process_environment', 'invoke', 'native_cost'):
            self.assertIs(getattr(runner, name), getattr(prior.shared, name))
        manifest, calls, records, output = self.collect()
        self.assertEqual((len(calls), manifest['valid_predictions']), (4, 4))
        self.assertEqual([r['packet_id'] for r in records], list(runner.measure.ORDER))
        self.assertEqual([c['payload'] for c in calls], [self.packets[pid]['payload'].encode() for pid in runner.measure.ORDER])
        self.assertEqual([r['response'] for r in records], [self.false_responses[pid] for pid in runner.measure.ORDER])
        self.assertEqual(len({c['session'] for c in calls}), 4)
        self.assertEqual([c['argv'][c['argv'].index('--max-budget-usd') + 1] for c in calls], ['1', '0.99', '0.98', '0.97'])
        self.assertEqual((manifest['native_budget_usd'], manifest['call_wall_seconds'], manifest['batch_wall_seconds']), ('1', 120, 300))
        for call in calls:
            for flag, value in (('--model', runner.MODEL), ('--effort', 'high'), ('--tools', ''), ('--system-prompt', runner.measure.SYSTEM_PROMPT)):
                self.assertEqual(call['argv'][call['argv'].index(flag) + 1], value)
            self.assertEqual(call['timeout'], 120)
            self.assertEqual(call['environment']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'], '500')
            self.assertNotIn('--resume', call['argv'])
        result = self.score(output)
        self.assertEqual(result['observed_counts'], {'answers': {'correct': 2, 'accepted': 4, 'planned': 4},
                                                    'validities': {'correct': 8, 'accepted': 16, 'planned': 16}})
        self.assertEqual(result['full_primary'], result['observed_counts'])
        self.assertEqual(result['invocations'], {'attempted': 4, 'accepted': 4, 'invalid': 0, 'unsent': 0, 'planned': 4})
        for diagnostic in result['diagnostics'].values():
            self.assertEqual(diagnostic['accepted_support_endpoints'], [])
            self.assertIsNone(diagnostic['answer_support_consistent'])
            self.assertEqual(diagnostic['undefined_reason'], 'no-accepted-support')

    def test_exact_judgments_wrong_answer_in_either_regime_and_support_diagnostics(self):
        exact = runner.measure.score_decisions(self.fixture, self.exact, {})
        self.assertEqual(exact['observed_counts'], {'answers': {'correct': 4, 'accepted': 4, 'planned': 4},
                                                   'validities': {'correct': 16, 'accepted': 16, 'planned': 16}})
        for pid in runner.measure.ORDER:
            predictions = deepcopy(self.exact)
            predictions[pid]['answer'] = not predictions[pid]['answer']
            result = runner.measure.score_decisions(self.fixture, predictions, {})
            diagnostic = result['diagnostics'][pid]
            self.assertFalse(diagnostic['answer_correct'])
            self.assertTrue(diagnostic['all_validities_correct'])
            self.assertEqual(diagnostic['accepted_support_endpoints'], [self.exact[pid]['answer']])
            self.assertFalse(diagnostic['answer_support_consistent'])
            self.assertIsNone(diagnostic['undefined_reason'])
            self.assertEqual(result['observed_counts']['answers']['correct'], 3)
            self.assertEqual(result['observed_counts']['validities']['correct'], 16)
        pid = runner.measure.ORDER[0]
        predictions = deepcopy(self.exact)
        predictions[pid]['validity'] = dict.fromkeys(self.ids[pid], True)
        diagnostic = runner.measure.score_decisions(self.fixture, predictions, {})['diagnostics'][pid]
        self.assertEqual(diagnostic['accepted_support_endpoints'], [False, True])
        self.assertIsNone(diagnostic['answer_support_consistent'])
        self.assertEqual(diagnostic['undefined_reason'], 'conflicting-support')
        predictions[pid]['validity'] = dict.fromkeys(self.ids[pid], False)
        copied = [r for label, r in zip(self.packets[pid]['private_order'], self.payloads[pid]['reports']) if label == 'F']
        self.assertEqual(len(copied), 3)
        predictions[pid]['validity'][copied[0]['report_id']] = True
        diagnostic = runner.measure.score_decisions(self.fixture, predictions, {})['diagnostics'][pid]
        self.assertTrue(diagnostic['root_copy_disagreements'][copied[0]['root_id']])
        self.assertEqual(sum(diagnostic['root_copy_disagreements'].values()), 1)
        self.assertEqual(diagnostic['accepted_support_endpoints'], [not self.exact[pid]['answer']])
        self.assertFalse(diagnostic['answer_support_consistent'])
        self.assertIsNone(diagnostic['undefined_reason'])

    def test_partial_atomic_failure_preserves_four_answers_and_sixteen_validities(self):
        order = runner.measure.ORDER
        for field in ('answer', 'validity'):
            malformed = deepcopy(self.exact[order[1]])
            if field == 'answer':
                malformed['answer'] = 0
            else:
                malformed['validity'][self.ids[order[1]][0]] = 0
            manifest, calls, records, output = self.collect(name=field, terminals=[json.dumps(self.exact[order[0]]), json.dumps(malformed)])
            self.assertEqual((len(calls), manifest['valid_predictions']), (2, 1))
            self.assertEqual(manifest['stop_reason'], 'invalid_answer')
            self.assertIsNone(records[1]['response'])
            result = self.score(output)
            self.assertIsNone(result['full_primary'])
            self.assertEqual(result['observed_counts'], {'answers': {'correct': 1, 'accepted': 1, 'planned': 4},
                                                        'validities': {'correct': 4, 'accepted': 4, 'planned': 16}})
            self.assertEqual([r['status'] for r in result['answers']], ['accepted', 'invalid', 'unsent', 'unsent'])
            self.assertEqual([r['status'] for r in result['validities']], ['accepted'] * 4 + ['invalid'] * 4 + ['unsent'] * 8)
            self.assertTrue(all(r['returned_answer'] is None and r['correct'] is None for r in result['answers'][1:]))
            self.assertTrue(all(r['returned_validity'] is None and r['correct'] is None for r in result['validities'][4:]))
            self.assertTrue(all(result['diagnostics'][pid] is None for pid in order[1:]))

    def test_first_native_or_resource_failure_stops_without_retry(self):
        for name in ('native', 'timeout', 'unknown-cost', 'budget', 'wall'):
            options = {'name': name}
            if name in ('native', 'timeout', 'unknown-cost'):
                options['failure'] = name
            elif name == 'budget':
                options['costs'] = [1.1]
            else:
                options['times'] = [0, 0, 300, 300]
            with self.subTest(name=name):
                manifest, calls, _, output = self.collect(**options)
                self.assertEqual(len(calls), 1)
                self.assertEqual(manifest['valid_predictions'], 1 if name in ('budget', 'wall') else 0)
                self.assertEqual(manifest['all_observed_costs_known'], name != 'unknown-cost')
                result = self.score(output)
                self.assertIsNone(result['full_primary'])
                self.assertEqual((len(result['answers']), len(result['validities'])), (4, 16))
                self.assertEqual(result['invocations']['unsent'], 3)
        manifest, calls, _, _ = self.collect(name='remaining', times=[0, 0, 220, 300, 300])
        self.assertEqual([c['timeout'] for c in calls], [120, 80])
        self.assertEqual(manifest['stop_reason'], 'batch_wall_exhausted')

    def test_changed_sources_or_payload_cannot_yield_scorable_collection(self):
        manifest, _, _, output = self.collect(changed_sources=True)
        self.assertEqual(manifest['status'], 'invalid')
        self.assertFalse(manifest['sources_unchanged'])
        self.assertTrue((output / 'manifest-invalid.json').exists())
        self.assertFalse((output / 'manifest.json').exists())
        self.fixture['packets'][0]['payload_sha256'] = '0' * 64
        manifest, calls, records, _ = self.collect(name='payload', expected_error=ValueError)
        self.assertEqual((calls, records), ([], []))
        self.assertEqual(manifest['invocations_scheduled'], 0)
        self.assertEqual(manifest['stop_reason'], 'collection_exception')

    def test_direct_scoring_rejects_truncated_or_mislabelled_fixture(self):
        for name in ('truncated', 'wrong-label', 'wrong-program', 'short-reports'):
            fixture = deepcopy(self.fixture)
            packet = fixture['packets'][0]
            if name == 'truncated':
                packet['private_order'].pop()
            elif name == 'wrong-label':
                packet['private_order'][0] = 'V'
            elif name == 'wrong-program':
                packet['program_id'] = 'R1'
            else:
                payload = json.loads(packet['payload'])
                payload['reports'].pop(0)
                packet['payload'] = json.dumps(payload)
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.measure.score_decisions(fixture, {}, {})

    def test_reused_native_sources_remain_pinned(self):
        for relative, expected in runner.PINNED.items():
            self.assertEqual(prior.shared.digest(runner.ROOT / relative), expected)
        with mock.patch.object(runner, 'digest', return_value='changed-source'):
            with self.assertRaisesRegex(ValueError, 'preserved native implementation changed'):
                runner.current_sources({'source_sha256_start': {}})

    def test_execution_seal_requires_new_decision_and_rejects_extra_call_or_byte_change(self):
        with self.execution_context() as execution:
            decision = self.root / runner.DECISION
            decision.write_text(json.dumps({'proceed': False, 'prepared_manifest_sha256': 'synthetic-prepared'}))
            with self.assertRaisesRegex(ValueError, 'separate execution decision'):
                runner.prepare_execution('synthetic-prepared')
            self.assertFalse(execution.exists())
            decision.write_text(json.dumps({'proceed': True, 'prepared_manifest_sha256': 'synthetic-prepared'}))
            identity = runner.prepare_execution('synthetic-prepared')
            fixture, _ = runner.sources(identity)
            self.assertEqual(fixture['request_order'], list(runner.measure.ORDER))
            self.assertEqual({p.name for p in execution.iterdir()}, {'system-prompt.txt', 'manifest.json'} | {pid + '.json' for pid in runner.measure.ORDER})
            seal_bytes = (execution / 'manifest.json').read_bytes()
            first = execution / (runner.measure.ORDER[0] + '.json')
            original = first.read_bytes()
            for name in ('bytes', 'extra-call', 'sources'):
                expected = identity
                if name == 'bytes':
                    first.write_bytes(original + b' ')
                else:
                    seal = json.loads(seal_bytes)
                    if name == 'extra-call':
                        seal['request_order'].append('fifth-call')
                    else:
                        seal['source_sha256'] = {}
                    (execution / 'manifest.json').write_text(json.dumps(seal))
                    expected = prior.shared.digest(execution / 'manifest.json')
                with self.subTest(name=name), mock.patch.object(runner, 'invoke') as invoke, self.assertRaises(ValueError):
                    runner.collect(expected)
                invoke.assert_not_called()
                first.write_bytes(original)
                (execution / 'manifest.json').write_bytes(seal_bytes)
            with self.assertRaises(FileExistsError):
                runner.prepare_execution('synthetic-prepared')

    def test_scorer_rejects_illegal_continuation_nonprefix_and_output_mutation(self):
        for name in ('continued-after-format', 'continued-after-native', 'prefix', 'output'):
            manifest, _, records, output = self.collect(name=name)
            if name.startswith('continued'):
                records[0].update(response=None, parse_failure='invalid_json')
                if name.endswith('native'):
                    records[0].update(native_acceptable=False, parse_failure=None, issues=['provider_refusal'])
                individual = output / ('01-' + records[0]['packet_id'] + '.json')
                individual.write_text(json.dumps(records[0]))
                manifest['output_sha256'][individual.name] = prior.shared.digest(individual)
            elif name == 'prefix':
                records[0], records[1] = records[1], records[0]
            else:
                records[0]['response']['answer'] = not records[0]['response']['answer']
            (output / 'responses.json').write_text(json.dumps(records))
            if name != 'output':
                manifest['output_sha256']['responses.json'] = prior.shared.digest(output / 'responses.json')
                (output / 'manifest.json').write_text(json.dumps(manifest))
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.score(output)
            self.assertFalse((output.parent / 'scored').exists())


if __name__ == '__main__':
    unittest.main()
