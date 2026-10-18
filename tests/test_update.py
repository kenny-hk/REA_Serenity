import copy
import json
from pathlib import Path
import tempfile
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
        p = POST | {'text': 'truncated', 'note_tweet': {'text': POST['text']}}
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
                'X_BEARER_TOKEN': 'test', 'ANTHROPIC_API_KEY': 'test', 'ANTHROPIC_MODEL': 'test'}), \
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
                'X_BEARER_TOKEN': 'test', 'ANTHROPIC_API_KEY': 'test', 'ANTHROPIC_MODEL': 'test', 'MAX_POSTS_PER_RUN': '1'}), \
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


if __name__ == '__main__':
    unittest.main()
