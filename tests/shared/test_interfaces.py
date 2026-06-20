from karsa.shared.domain.repository import Repository
from karsa.shared.domain.unit_of_work import UnitOfWork
from karsa.shared.events.outbox import EventOutbox
from karsa.shared.events.publisher import EventPublisher
from karsa.shared.domain.aggregate import AggregateRoot
from karsa.shared.application.command_handler import CommandHandler
from karsa.shared.application.query_handler import QueryHandler

class DummyAggregate(AggregateRoot):
    def __init__(self):
        super().__init__()
        self.aggregate_id = "dummy-1"

class DummyRepo(Repository):
    def add(self, agg):
        super().add(agg)
    def get(self, id):
        super().get(id)

class DummyUoW(UnitOfWork):
    def commit(self):
        super().commit()
    def rollback(self):
        super().rollback()

class DummyOutbox(EventOutbox):
    def save_events(self, events):
        super().save_events(events)
    def get_unpublished_events(self, limit=100):
        super().get_unpublished_events()
        return []
    def mark_as_published(self, event_ids):
        super().mark_as_published(event_ids)

class DummyPublisher(EventPublisher):
    def publish(self, events):
        super().publish(events)
    
class DummyCmdHandler(CommandHandler):
    def handle(self, cmd):
        super().handle(cmd)
    
class DummyQryHandler(QueryHandler):
    def handle(self, qry):
        super().handle(qry)

def test_interfaces():
    r = DummyRepo()
    r.add(DummyAggregate())
    r.get("1")
    
    u = DummyUoW()
    u.commit()
    u.rollback()
    
    with DummyUoW() as w:
        pass
        
    try:
        with DummyUoW() as w2:
            raise ValueError()
    except:
        pass
        
    o = DummyOutbox()
    o.save_events([])
    o.get_unpublished_events()
    o.mark_as_published([])
    
    p = DummyPublisher()
    p.publish([])
    
    ch = DummyCmdHandler()
    ch.handle(None)
    
    qh = DummyQryHandler()
    qh.handle(None)
