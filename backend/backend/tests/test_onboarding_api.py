import os, importlib

os.environ['APP_ENV'] = 'dev'
import app.main as main
importlib.reload(main)

from app.routes.onboarding import onboarding_state, onboarding_event


def test_state_empty_flags_false():
    s = onboarding_state()
    body = s.body.decode('utf-8')
    import json
    data = json.loads(body)
    assert data['seen_welcome'] is False
    assert data['steps']['created_project'] is False
    assert data['steps']['rendered_video'] is False
    assert data['steps']['exported_video'] is False


def test_events_toggle_flags_idempotent():
    # welcome_seen
    r1 = onboarding_event({'event': 'welcome_seen'})
    assert r1['ok'] is True
    # create project
    r2 = onboarding_event({'event': 'created_project'})
    assert r2['ok'] is True
    # duplicate should be ok and not error
    r3 = onboarding_event({'event': 'created_project'})
    assert r3['ok'] is True
    # state reflects flags
    s = onboarding_state()
    import json
    data = json.loads(s.body.decode('utf-8'))
    assert data['seen_welcome'] is True
    assert data['steps']['created_project'] is True
