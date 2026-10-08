import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import time
from contextlib import closing

import httpx
import pytest
from fastapi.testclient import TestClient

from quantum_lab_agent.provider import Settings
from quantum_lab_agent.workbench import create_app


class Model:
    async def complete(self, messages, tools, deadline):
        return {"role": "assistant", "content": "secret-value", "tool_calls": []}


def app(tmp_path, model=Model):
    return create_app(settings=Settings(api_key="secret-value"), root=tmp_path,
                      model_factory=lambda client: model(),
                      transport=httpx.MockTransport(lambda r: httpx.Response(500)))


def wait(client, identity):
    for _ in range(200):
        data = client.get(f"/api/runs/{identity}").json()
        if data["status"] not in ("queued", "running"):
            return data
        time.sleep(.02)
    raise AssertionError("run did not finish")


def test_persist_redact_and_reconnect(tmp_path):
    with TestClient(app(tmp_path)) as c:
        config = c.get('/api/config').json()
        assert config['model'] == 'google/gemma-4-e2b'
        assert 'api_key' not in config and 'qec_url' not in config
        body = {'request_id': 'a' * 32, 'family': 'quantum', 'prompt': 'hello'}
        response = c.post('/api/runs', json=body)
        assert response.status_code == 202
        identity = response.json()['run_id']
        data = wait(c, identity)
        assert data['status'] == 'no_tool_calls'
        assert c.post('/api/runs', json=body).json()['run_id'] == identity
        assert 'secret-value' not in c.get(f'/api/runs/{identity}/export.json').text
        assert 'No verified tool evidence' in c.get(f'/api/runs/{identity}/export.md').text
        events = c.get(f'/api/runs/{identity}/events?after=0').json()['events']
        assert events
        assert c.get(f'/api/runs/{identity}/events?after={events[-1]["seq"]}').json()['events'] == []
    with TestClient(app(tmp_path)) as c:
        assert c.get('/api/runs').json()[0]['run_id'] == identity
        assert c.get(f'/api/runs/{identity}').json()['status'] == 'no_tool_calls'


def test_bounds_and_family(tmp_path):
    with TestClient(app(tmp_path)) as c:
        base = {'request_id': 'b'*32, 'family': 'quantum', 'prompt': 'hello'}
        for extra in ({'reports': 1}, {'family': 'auto'}, {'limits': {'seconds': 1801}},
                      {'prompt': 'x'*8001}, {'fixture': True}):
            assert c.post('/api/runs', json=base | extra).status_code == 422
        assert c.post('/api/runs', json=base, headers={'origin': 'https://evil.test'}).status_code == 403
        assert c.get('/api/runs/unknown').status_code == 404
        assert c.get('/api/runs/'+'a'*32+'/graphics/'+'b'*64+'.svg').status_code == 404


def test_active_timeout_and_id_conflict(tmp_path):
    class Slow:
        async def complete(self, *args):
            await asyncio.sleep(1)
    with TestClient(app(tmp_path, Slow)) as c:
        body = {'request_id': 'c'*32, 'family': 'qec', 'prompt': 'hello',
                'limits': {'seconds': .2}}
        assert c.post('/api/runs', json=body).status_code == 202
        assert c.post('/api/runs', json=body | {'request_id': 'd'*32}).status_code == 409
        assert c.post('/api/runs', json=body | {'prompt': 'changed'}).status_code == 409
        assert wait(c, body['request_id'])['status'] == 'time_budget'


def test_restart_marks_unfinished_interrupted(tmp_path):
    with TestClient(app(tmp_path)):
        pass
    with sqlite3.connect(tmp_path / 'trace.sqlite3') as db:
        db.execute("INSERT INTO web_runs VALUES(?,?,'running',0)",
                   ('e'*32, '{"family":"qec","prompt":"crash"}'))
        db.execute("INSERT INTO runs VALUES(?,0,'crash')", ('e'*32,))
    with TestClient(app(tmp_path)) as c:
        assert c.get('/api/runs/'+'e'*32).json()['status'] == 'interrupted'


def test_fixture_quantum_and_qec(tmp_path):
    from quantum_lab_agent.workbench_fixture import create_fixture_app
    with TestClient(create_fixture_app(root=tmp_path)) as c:
        assert c.get('/api/config').json()['fixture'] is True
        for family in ('quantum', 'qec'):
            identity = ('a' if family == 'quantum' else 'b') * 32
            body = {'request_id': identity, 'family': family, 'prompt': 'fixture',
                    'reports': 1 if family == 'qec' else 0,
                    'limits': {'max_tools': 6, 'max_steps': 7, 'seconds': 60}}
            assert c.post('/api/runs', json=body).status_code == 202
            data = wait(c, identity)
            assert data['status'] == ('completed' if family == 'quantum' else 'report_ready')
            if family == 'quantum':
                plots = next(e['data']['result'] for e in data['events']
                             if e['kind'] == 'tool_result' and
                             e['data']['result'].get('kind') == 'quantum_plots')
                filename = plots['graphics']['circuit_svg']['file']
                route = f'/api/runs/{identity}/graphics/{filename}'
                assert c.get(route).headers['content-type'].startswith('image/svg+xml')
                assert c.get(route.replace(identity, 'b'*32)).status_code == 404
                (tmp_path / 'quantum' / filename).write_text('tampered')
                assert c.get(route).status_code == 409
                simulation = next(e['data']['result'] for e in data['events']
                                  if e['kind'] == 'tool_result' and
                                  e['data']['result'].get('kind') == 'quantum_simulation')
                assert sum(simulation['counts'].values()) == 128
                assert simulation['premeasurement_fidelity'] > .999999
            else:
                assert 'comparison-fixture' in data['grounded_output']


def test_provider_failure_is_not_completion(tmp_path):
    class Broken:
        async def complete(self, *args):
            raise httpx.ConnectError('secret-value')
    with TestClient(app(tmp_path, Broken)) as c:
        identity = 'f'*32
        c.post('/api/runs', json={'request_id': identity, 'family': 'qec', 'prompt': 'test'})
        data = wait(c, identity)
        assert data['status'] == 'provider_error'
        assert 'secret-value' not in json.dumps(data)


def test_uncertain_b_post_is_never_duplicated(tmp_path):
    posts = []
    class Repeat:
        async def complete(self, messages, tools, deadline):
            return {'role': 'assistant', 'tool_calls': [
                {'id': 'call', 'function': {'name': 'qec_sample', 'arguments': '{}'}}]}
    def transport(request):
        posts.append(request)
        raise httpx.ConnectError('secret-value')
    api = create_app(settings=Settings(api_key='secret-value'), root=tmp_path,
                     model_factory=lambda client: Repeat(), transport=httpx.MockTransport(transport))
    with TestClient(api) as c:
        identity = 'a'*32
        c.post('/api/runs', json={'request_id': identity, 'family': 'qec', 'prompt': 'test',
                                 'limits': {'max_steps': 3, 'max_tools': 2}})
        data = wait(c, identity)
        assert data['status'] == 'tool_budget'
        assert len(posts) == 1
        assert len([e for e in data['events'] if e['kind'] == 'tool_error']) == 2
        assert 'Uncertain prior submission' in json.dumps(data)
        assert 'secret-value' not in c.get(f'/api/runs/{identity}/export.json').text


def test_request_size_boundary(tmp_path):
    with TestClient(app(tmp_path)) as c:
        assert c.post('/api/runs', content=b'x'*40001).status_code == 413


def test_fixture_root_cannot_be_reopened_as_production(tmp_path):
    from quantum_lab_agent.workbench_fixture import create_fixture_app
    with TestClient(create_fixture_app(root=tmp_path)):
        pass
    with pytest.raises(ValueError, match='mode'), TestClient(app(tmp_path)):
        pass


def test_shutdown_is_bounded_and_does_not_claim_cancellation(tmp_path):
    class Slow:
        async def complete(self, *args):
            await asyncio.sleep(4)
            return {'role': 'assistant', 'content': 'done'}
    started = time.monotonic()
    with TestClient(app(tmp_path, Slow)) as c:
        c.post('/api/runs', json={'request_id': 'a'*32, 'family': 'qec', 'prompt': 'test'})
    assert time.monotonic() - started < 3.5
    with sqlite3.connect(tmp_path / 'trace.sqlite3') as db:
        assert db.execute('SELECT status FROM web_runs').fetchone()[0] == 'interrupted'


def test_request_identity_uses_original_not_redacted_payload(tmp_path):
    body = {'request_id': 'a'*32, 'family': 'qec', 'prompt': 'token=one'}
    with TestClient(app(tmp_path)) as c:
        assert c.post('/api/runs', json=body).status_code == 202
        wait(c, body['request_id'])
        assert c.post('/api/runs', json=body | {'prompt': 'token=two'}).status_code == 409
    with TestClient(app(tmp_path)) as c:
        assert c.post('/api/runs', json=body).status_code == 202
        assert c.post('/api/runs', json=body | {'prompt': 'token=two'}).status_code == 409
    content = (tmp_path / 'trace.sqlite3').read_bytes()
    assert b'token=one' not in content and b'token=two' not in content


def test_graphics_reject_parent_junction(tmp_path):
    root, outside = tmp_path / 'root', tmp_path / 'outside'
    outside.mkdir()
    content = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    digest = hashlib.sha256(content).hexdigest()
    filename = digest + '.svg'
    (outside / filename).write_bytes(content)
    with TestClient(app(root)):
        pass
    with closing(sqlite3.connect(root / 'trace.sqlite3')) as db, db:
        db.execute("INSERT INTO web_runs VALUES(?,?,'completed',0)",
                   ('a'*32, '{"family":"quantum","prompt":"test"}'))
        db.execute("INSERT INTO runs VALUES(?,0,'test')", ('a'*32,))
        db.execute("INSERT INTO events(run_id,created,kind,data) VALUES(?,0,'tool_result',?)",
                   ('a'*32, json.dumps({'result': {'kind': 'quantum_plots', 'graphics': {
                       'circuit_svg': {'file': filename, 'sha256': digest}}}})))
    junction = root / 'quantum'
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)],
                       check=True, capture_output=True)
    else:
        junction.symlink_to(outside, target_is_directory=True)
    try:
        with TestClient(app(root)) as c:
            assert c.get(f'/api/runs/{"a"*32}/graphics/{filename}').status_code == 404
    finally:
        if os.name == 'nt':
            junction.rmdir()
        else:
            junction.unlink()
    assert (outside / filename).read_bytes() == content
