import asyncio
import json

from automation.backend import BackendService


def test_backend_honors_requested_rounds_over_old_cap(tmp_path, monkeypatch):
    config=tmp_path/'config'/'settings.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'mockMode':True,'maxRounds':1}))
    monkeypatch.setattr(BackendService,'write_event',staticmethod(lambda e:None))
    monkeypatch.setattr('automation.backend.RollingEventLogger',lambda **kwargs:lambda e:None)
    monkeypatch.setattr(BackendService,'_save_result',lambda *args:None)
    service=BackendService(str(config))
    events=[]
    service.event_bus.on_any(lambda e:events.append(e))
    async def run():
        await service.start_task({'gameId':'clash_royale','taskId':'classic_1v1_loop',
            'parameters':{'targetRounds':3},'mockRounds':[3,0,0,3]})
        return await service.runner
    result=asyncio.run(run())
    assert result.round_count==3
    assert result.target_reached
    assert service.current_task.next_round_count==2
    assert sum(e['type']=='task_completed' for e in events)==1
    assert result.as_protocol_dict()['remainingRounds']==0
