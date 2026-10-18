import copy
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
from scripts import update

POST = {'id': '123', 'created_at': '2026-10-17T12:00:00Z', 'text': '$TEST has strong demand but capacity is a risk.'}
ITEM = {'ticker': 'TEST', 'company': 'Test Company', 'stance': 'bullish',
        'summary': 'Positive on demand; flags capacity risk.', 'evidence': 'strong demand', 'risks': ['Capacity']}
STATE = {'schema_version': 1, 'account': 'aleabitoreddit', 'status': 'ok', 'last_success': '2026-10-16T00:00:00Z',
         'since_id': '100', 'mentions': [], 'posts_checked': 1, 'coverage_start': '2026-10-16T00:00:00Z'}


class ValidationTests(unittest.TestCase):
    def test_source_url_derived_from_actual_post(self):
        item = ITEM | {'url': 'https://example.org/fake'}
        result = update.validate_mentions({'mentions': [item]}, POST)[0]
        self.assertEqual(result['url'], 'https://x.com/aleabitoreddit/status/123')

    def test_hallucinated_evidence_rejected(self):
        with self.assertRaises(ValueError):
            update.validate_mentions({'mentions': [ITEM | {'evidence': 'buy now'}]}, POST)

    def test_mixed_stances_remain_per_stock(self):
        items = [ITEM, ITEM | {'ticker': 'OTHER', 'stance': 'bearish'}]
        self.assertEqual([m['stance'] for m in update.validate_mentions({'mentions': items}, POST)], ['bullish', 'bearish'])

    def test_duplicate_ticker_rejected(self):
        with self.assertRaises(ValueError):
            update.validate_mentions({'mentions': [ITEM, ITEM]}, POST)

    def test_invalid_stance_and_script_ticker_rejected(self):
        for change in [{'stance': 'buy'}, {'ticker': '<script>'}, {'risks': 'risk'}, {'summary': ''}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                update.validate_mentions({'mentions': [ITEM | change]}, POST)

    def test_long_post_text_used(self):
        for field in ['note_post', 'note_tweet']:
            p = POST | {'text': 'truncated', field: {'text': POST['text']}}
            self.assertEqual(len(update.validate_mentions({'mentions': [ITEM]}, p)), 1)

    def test_no_mentions_is_valid(self):
        self.assertEqual(update.validate_mentions({'mentions': []}, POST), [])


class PipelineTests(unittest.TestCase):
    def test_merge_is_nonmutating_and_deduplicates(self):
        state = copy.deepcopy(STATE)
        mentions = update.validate_mentions({'mentions': [ITEM]}, POST)
        first = update.merge(state, [POST], mentions, '2026-10-18T00:00:00Z', 'test-model')
        second = update.merge(first, [], mentions, '2026-10-18T01:00:00Z', 'test-model')
        self.assertEqual(len(second['mentions']), 1)
        self.assertEqual(second['since_id'], '123')
        self.assertEqual(state, STATE)
        self.assertEqual(second['coverage_start'], STATE['coverage_start'])

    def test_pagination_fetches_all_and_sorts_oldest_first(self):
        with patch.object(update, 'request_json', side_effect=[{'data': {'id': '5'}},
             {'data': [POST | {'id': '125'}], 'meta': {'next_token': 'next'}},
             {'data': [POST], 'meta': {}}]) as request:
            posts = update.fetch_posts(STATE, 'secret')
        self.assertEqual([p['id'] for p in posts], ['123', '125'])
        self.assertIn('pagination_token=next', request.call_args[0][0])
        self.assertIn('since_id=100', request.call_args[0][0])

    def test_failure_preserves_cursor_and_last_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tracker.json'
            path.write_text(json.dumps(STATE))
            with patch.object(update, 'DATA', path), patch.dict(update.os.environ, {
                'X_BEARER_TOKEN': 'test', 'OPENAI_API_KEY': 'test', 'OPENAI_MODEL': 'test', 'CLASSIFIER_PROVIDER': 'openai'}), \
                patch.object(update, 'fetch_posts', return_value=[POST]), \
                patch.object(update, 'classify', side_effect=ValueError('bad evidence')):
                self.assertEqual(update.main(), 1)
            saved = json.loads(path.read_text())
            self.assertEqual(saved['status'], 'error')
            self.assertEqual(saved['since_id'], STATE['since_id'])
            self.assertEqual(saved['last_success'], STATE['last_success'])

    def test_budget_cap_advances_only_to_processed_post(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tracker.json'
            path.write_text(json.dumps(STATE))
            with patch.object(update, 'DATA', path), patch.dict(update.os.environ, {
                'X_BEARER_TOKEN': 'test', 'OPENAI_API_KEY': 'test', 'OPENAI_MODEL': 'test', 'CLASSIFIER_PROVIDER': 'openai', 'MAX_POSTS_PER_RUN': '1'}), \
                patch.object(update, 'fetch_posts', return_value=[POST, POST | {'id': '124'}]), \
                patch.object(update, 'classify', return_value=[]):
                self.assertEqual(update.main(), 0)
            saved = json.loads(path.read_text())
            self.assertEqual(saved['since_id'], '123')
            self.assertEqual(saved['backlog'], 1)

    def test_missing_credentials_not_reported_as_live(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tracker.json'
            path.write_text(json.dumps(STATE))
            with patch.object(update, 'DATA', path), patch.dict(update.os.environ, {}, clear=True):
                self.assertEqual(update.main(), 0)
            self.assertEqual(json.loads(path.read_text())['status'], 'awaiting_configuration')


class OpenAIClassifierTests(unittest.TestCase):
    def test_responses_api_extracts_text_and_reuses_validation(self):
        response = {'status': 'completed', 'output': [
            {'type': 'reasoning'}, {'type': 'message', 'content': [
                {'type': 'output_text', 'text': json.dumps({'mentions': [ITEM]})}]}]}
        with patch.object(update, 'request_json', return_value=response) as request:
            result = update.classify(POST, 'test-key', 'test-model')
        self.assertEqual(result[0]['ticker'], 'TEST')
        self.assertEqual(request.call_args.args[0], 'https://api.openai.com/v1/responses')
        self.assertFalse(request.call_args.args[2]['store'])

    def test_incomplete_response_rejected(self):
        with patch.object(update, 'request_json', return_value={'status': 'incomplete'}):
            with self.assertRaises(ValueError):
                update.classify(POST, 'test-key', 'test-model')

    def test_codex_environment_excludes_provider_secrets(self):
        with patch.dict(update.os.environ, {'X_BEARER_TOKEN': 'secret', 'OPENAI_API_KEY': 'secret',
                        'CODEX_API_KEY': 'secret', 'GH_TOKEN': 'secret', 'PATH': 'test'}, clear=True):
            self.assertEqual(update.codex_environment(), {'PATH': 'test'})

    def test_codex_refuses_github_ci(self):
        with patch.dict(update.os.environ, {'GITHUB_ACTIONS': 'true'}):
            with self.assertRaises(RuntimeError):
                update.check_codex_login()

    def test_codex_refuses_api_key_login(self):
        with patch.dict(update.os.environ, {}, clear=True), patch.object(update, 'codex_command', return_value=['codex']), \
             patch.object(update.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Logged in using an API key', '')):
            with self.assertRaises(RuntimeError):
                update.check_codex_login()

    def test_codex_output_validated_without_api_fallback(self):
        def run(args, **kwargs):
            path = Path(args[args.index('--output-last-message') + 1])
            path.write_text(json.dumps({'mentions': [ITEM]}))
            self.assertIn('forced_login_method="chatgpt"', args)
            self.assertIn('features.shell_tool=false', args)
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(update, 'codex_command', return_value=['codex']), \
             patch.object(update.subprocess, 'run', side_effect=run), patch.object(update, 'request_json') as api:
            self.assertEqual(update.classify_codex(POST)[0]['ticker'], 'TEST')
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
