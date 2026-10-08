"""Explicit OFFLINE acceptance entrypoint; never selected by a production request."""
import asyncio
import json
import os

import httpx

from .provider import Settings
from .workbench import create_app


class FixtureModel:
    async def complete(self, messages, tools, deadline):
        await asyncio.sleep(.15)
        results = [json.loads(m['content']) for m in messages if m['role'] == 'tool']
        quantum = tools[0]['function']['name'] == 'build_circuit'
        if not quantum:
            name, args = 'qec_read_report', {'result_id': 'comparison-fixture'}
            if results:
                return {'role': 'assistant', 'content': '離線 QEC fixture 完成；不是實際 B 實驗。'}
        elif not results:
            name, args = 'build_circuit', {'target': 'bell', 'preset': 'bell', 'qubits': 2}
        elif len(results) == 1:
            name, args = 'run_simulation', {'circuit_id': results[0]['artifact_id'], 'shots': 128}
        elif len(results) == 2:
            name, args = 'plot', {'result_id': results[1]['artifact_id']}
        else:
            return {'role': 'assistant', 'content': '固定測試規劃；數值來自本機 Aer。'}
        return {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': str(len(results)), 'type': 'function',
             'function': {'name': name, 'arguments': json.dumps(args)}}]}


def mock_b(request):
    if request.method == 'GET' and request.url.path == '/api/results/comparison-fixture':
        return httpx.Response(200, json={
            'kind': 'qec', 'artifact_id': 'comparison-fixture', 'dataset_id': 'dataset-fixture',
            'results': [{'decoder': decoder, 'prediction_key': decoder, 'shots': 32,
                         'errors': 1, 'logical_error_rate': 1 / 32, 'ci': [0.001, .2],
                         'decode_seconds': .001} for decoder in ('mwpm', 'lookup')]})
    raise AssertionError('Unexpected offline HTTP request')


def create_fixture_app(root=None):
    return create_app(settings=Settings(model='OFFLINE fixture / real Aer',
                                       qec_url='http://fixture.invalid'),
                      profile='offline-fixture',
                      root=root or os.getenv('QLA_FIXTURE_ROOT', '.qla/acceptance-fixture'),
                      model_factory=lambda client: FixtureModel(),
                      transport=httpx.MockTransport(mock_b), fixture=True)
