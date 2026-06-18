import time
import os
from karsa.bootstrap import get_postgres_pool
from karsa.shared.infrastructure.event_journal import EventJournalRepository, ProjectionCheckpointRepository
from karsa.portfolio.infrastructure.storage.postgres_read_repositories import PostgresValuationRepository, PostgresPositionRepository, PostgresCashLedgerRepository
from karsa.portfolio.services import PortfolioProjectionService
# from karsa.attribution.application.projections import AttributionProjectionService
import json

def process_events(pool):
    with pool.connection() as conn:
        journal_repo = EventJournalRepository(conn)
        checkpoint_repo = ProjectionCheckpointRepository(conn)
        val_repo = PostgresValuationRepository(pool)
        pos_repo = PostgresPositionRepository(pool)
        cash_repo = PostgresCashLedgerRepository(pool)
        
        from karsa.portfolio.services import PortfolioValuationService, ExposureCalculationService, BenchmarkRegistryService
        exposure_service = ExposureCalculationService()
        benchmark_service = BenchmarkRegistryService()
        val_service = PortfolioValuationService(val_repo, exposure_service, benchmark_service)
        
        proj_service = PortfolioProjectionService(pos_repo, cash_repo, val_service)

        # attr_service = AttributionProjectionService(conn)

        from karsa.cio.projections import CioProjectionService
        cio_proj_service = CioProjectionService(conn)

        from karsa.thesis.projections import ThesisProjectionService
        thesis_proj_service = ThesisProjectionService(conn)

        projection_name = "portfolio_read_models"
        
        checkpoint = checkpoint_repo.lock_checkpoint(projection_name)
        last_seq = checkpoint["last_processed_sequence"]

        events = journal_repo.read_events(after_sequence=last_seq, batch_size=100)
        
        if not events:
            return 0

        for event in events:
            try:
                payload = event["payload"]
                event_type = event["event_type"]
                
                # The existing handlers in PortfolioProjectionService expect a dictionary.
                if event_type == "OrderFilledEvent":
                    proj_service.consume_order_filled(payload)
                elif event_type == "PortfolioRebalancedEvent":
                    pass # Or relevant handlers
                elif event_type == "PortfolioDecisionMadeEvent":
                    cio_proj_service.consume_portfolio_decision_made(payload)
                elif event_type == "ThesisProposedEvent":
                    thesis_proj_service.handle_thesis_proposed(payload)
                elif event_type == "ThesisActivatedEvent":
                    thesis_proj_service.handle_thesis_activated(payload)
                
                # elif event_type == "DecisionLineageCreatedEvent":
                #     attr_service.consume_decision_lineage_created(payload)
                # elif event_type == "LineageNodeAddedEvent":
                #     attr_service.consume_lineage_node_added(payload)
                # elif event_type == "AttributionFactGeneratedEvent":
                #     attr_service.consume_attribution_fact_generated(payload)
                # elif event_type == "AttributionAssessmentSealedEvent":
                #     attr_service.consume_attribution_assessment_sealed(payload)

                
                last_seq = event["global_sequence"]
            except Exception as e:
                print(f"Poison event {event['global_sequence']}: {e}")
                checkpoint_repo.update_checkpoint(projection_name, last_seq, status='FAILED')
                conn.commit()
                raise e
            
        checkpoint_repo.update_checkpoint(projection_name, last_seq, status='RUNNING')
        conn.commit()
        return len(events)

def main():
    print("Starting projection worker...")
    with get_postgres_pool() as pool:
        while True:
            try:
                count = process_events(pool)
                if count == 0:
                    time.sleep(1.0)
                else:
                    print(f"Processed {count} events.")
            except Exception as e:
                print(f"Worker crashed: {e}")
                time.sleep(5.0)

if __name__ == "__main__":
    main()
