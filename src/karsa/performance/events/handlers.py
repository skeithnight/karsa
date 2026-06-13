from .application.ingestion import PerformanceEventIngestionService

def register_performance_handlers(bus, ingestion_service: PerformanceEventIngestionService):
    def on_attribution_calculated(event):
        ingestion_service.handle_attribution_calculated(event)

    bus.subscribe("AttributionCalculatedEvent", on_attribution_calculated)
