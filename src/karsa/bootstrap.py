import os
from psycopg_pool import ConnectionPool
from typing import Dict, Any

from karsa.risk.repositories import (
    PostgresRiskEvaluationRepository,
    PostgresCovarianceForecastRepository,
    PostgresStressEvaluationRepository
)
from karsa.risk.services import (
    RiskEvaluationService,
    StressTestingService,
    CovarianceForecastService,
    ConcentrationRiskService,
    LiquidityRiskService
)
from karsa.risk.ports import EventPublisherPort, ReturnsDataPort, RegimeStatePort, ObjectStorePort

from karsa.cio.repositories import PostgresCIODecisionRepository
from karsa.cio.services import CIODecisionService, PortfolioOrchestrationService
from karsa.cio.ports import DecisionJournalPort, GovernanceExceptionPort

from karsa.post_mortem.repositories import (
    PostgresPostMortemRecordRepository,
    PostgresRecommendationRepository
)
from karsa.post_mortem.services import PostMortemService, RecommendationRegistryService
from karsa.post_mortem.ports import SignatureValidationPort

from karsa.portfolio.api import PortfolioAPI
from karsa.portfolio.services import PortfolioProjectionService, PortfolioValuationService
from karsa.portfolio.infrastructure.storage.postgres_read_repositories import PostgresValuationRepository, PostgresPositionRepository, PostgresCashLedgerRepository
from karsa.memory.infrastructure.event.postgres_event_bus import PostgresEventBus

from karsa.execution.application.services import (
    OrderPEPService, OrderRoutingService, FillService, ExecutionStateProjectionService
)

from karsa.memory.domain.service.snapshot_service import SnapshotService
from karsa.memory.domain.service.schema_registry import SchemaRegistryService
from karsa.memory.domain.model.events import EventBus
from karsa.memory.infrastructure.storage.in_memory_schema_repository import InMemorySchemaRepository
from karsa.memory.infrastructure.storage.in_memory_snapshot_repository import InMemorySnapshotRepository
from karsa.memory.infrastructure.storage.local_blob_storage import LocalBlobStorage
from karsa.memory.infrastructure.event.mock_event_bus import MockEventBus

class DummyPublisher(EventPublisherPort):
    def publish(self, event: Any) -> None:
        pass

class DummyReturnsPort(ReturnsDataPort):
    def get_historical_returns(self, asset_urns, start_date, end_date):
        return {a: [0.0] for a in asset_urns}

class DummyRegimePort(RegimeStatePort):
    def get_active_regime_multiplier(self):
        return {"regime_state_urn": "urn:karsa:regime:neutral", "volatility_multiplier": 1.0}

class DummyObjectStore(ObjectStorePort):
    def save_matrix(self, matrix_urn: str, data: list) -> None: pass
    def get_matrix(self, matrix_urn: str) -> list: return []

class DummyDecisionJournal(DecisionJournalPort):
    def verify_entry_exists(self, ref: str) -> bool: return True
    def get_journal_expectations(self, *args, **kwargs) -> Any: return []
    def verify_journal_exists(self, *args, **kwargs) -> bool: return True

class DummyGovernancePort(GovernanceExceptionPort):
    def verify_exception(self, exc_id: str) -> bool: return True
    def verify_exception_token(self, *args, **kwargs) -> bool: return True

class DummySignatureValidator(SignatureValidationPort):
    def validate_caller_signature(self, signature: str, payload: Dict[str, Any]) -> bool: return True
    def validate_signature(self, *args, **kwargs) -> bool: return True

def get_postgres_pool() -> ConnectionPool:
    db_name = os.environ.get("POSTGRES_DB", "karsa_db")
    db_user = os.environ.get("POSTGRES_USER", "karsa")
    db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
    db_host = os.environ.get("POSTGRES_HOST", "postgres")
    db_port = os.environ.get("POSTGRES_PORT", "5432")
    conninfo = f"dbname={db_name} user={db_user} password={db_pass} host={db_host} port={db_port}"
    return ConnectionPool(conninfo, min_size=1, max_size=5)

class ApplicationContainer:
    def __init__(self):
        self.pool = get_postgres_pool()
        self.conn = self.pool.getconn()
        self.conn.autocommit = True
        
        # Event Bus (shared across services)
        self.event_bus = PostgresEventBus(self.pool)

        # Risk Setup
        self.risk_repo = PostgresRiskEvaluationRepository(self.conn)
        self.cov_repo = PostgresCovarianceForecastRepository(self.conn)
        self.stress_repo = PostgresStressEvaluationRepository(self.conn)
        
        self.risk_publisher = DummyPublisher()
        self.returns_port = DummyReturnsPort()
        self.regime_port = DummyRegimePort()
        self.object_store = DummyObjectStore()
        
        self.concentration_svc = ConcentrationRiskService()
        self.liquidity_svc = LiquidityRiskService()
        
        self.stress_service = StressTestingService(self.stress_repo, self.risk_publisher)
        self.cov_service = CovarianceForecastService(self.cov_repo, self.object_store, self.risk_publisher)
        self.risk_service = RiskEvaluationService(
            record_repo=self.risk_repo,
            cov_repo=self.cov_repo,
            returns_port=self.returns_port,
            regime_port=self.regime_port,
            object_store=self.object_store,
            publisher=self.risk_publisher,
            concentration_service=self.concentration_svc,
            liquidity_service=self.liquidity_svc
        )

        # CIO Setup
        self.cio_repo = PostgresCIODecisionRepository(self.conn)
        self.decision_journal = DummyDecisionJournal()
        self.gov_port = DummyGovernancePort()
        from cryptography.hazmat.primitives.asymmetric import ed25519
        dummy_cio_key = ed25519.Ed25519PrivateKey.generate()
        self.decision_service = CIODecisionService(
            decision_repo=self.cio_repo,
            journal_port=self.decision_journal,
            governance_port=self.gov_port,
            event_publisher=self.event_bus,
            private_key=dummy_cio_key
        )
        self.orchestration_service = PortfolioOrchestrationService(self.cio_repo)
        
        # Post Mortem Setup
        self.pm_record_repo = PostgresPostMortemRecordRepository(self.conn)
        self.pm_rec_repo = PostgresRecommendationRepository(self.conn)
        self.signature_validator = DummySignatureValidator()
        self.pm_service = PostMortemService(self.pm_record_repo, self.pm_rec_repo, self.risk_publisher)
        self.pm_rec_service = RecommendationRegistryService(self.pm_rec_repo, self.risk_publisher, self.signature_validator)
        
        # Execution Setup
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from karsa.execution.infrastructure.adapters.postgres_decision_auth_adapter import PostgresDecisionAuthorizationAdapter
        class DummyRequestRepo:
            def save(self, *args, **kwargs): pass
            def get_by_execution_id(self, *args, **kwargs): return None
        class DummyRoutingRepo: pass
        class DummyFillRepo: pass
        class DummyBrokerAdapter: pass
        class DummyGovAuthPort:
            def verify_governance_exception(self, *args, **kwargs): return True
            
        dummy_pep_key = ed25519.Ed25519PrivateKey.generate()
        self.pep_service = OrderPEPService(
            request_repo=DummyRequestRepo(),
            decision_auth_port=PostgresDecisionAuthorizationAdapter(self.conn, dummy_cio_key.public_key()),
            gov_auth_port=DummyGovAuthPort(),
            pep_private_key=dummy_pep_key
        )
        self.routing_service = OrderRoutingService(
            routing_repo=DummyRoutingRepo(),
            request_repo=DummyRequestRepo(),
            broker_adapter=DummyBrokerAdapter(),
            pep_private_key=dummy_pep_key
        )
        self.fill_service = FillService(
            fill_repo=DummyFillRepo(),
            routing_repo=DummyRoutingRepo(),
            event_publisher=None
        )
        self.projection_service = ExecutionStateProjectionService(
            request_repo=DummyRequestRepo(),
            routing_repo=DummyRoutingRepo(),
            fill_repo=DummyFillRepo()
        )
        
        # Portfolio Setup
        self.val_repo = PostgresValuationRepository(self.pool)
        self.pos_repo = PostgresPositionRepository(self.pool)
        self.cash_repo = PostgresCashLedgerRepository(self.pool)
        from karsa.portfolio.services import ExposureCalculationService, BenchmarkRegistryService
        self.exposure_service = ExposureCalculationService()
        self.benchmark_service = BenchmarkRegistryService()
        self.portfolio_val_service = PortfolioValuationService(self.val_repo, self.exposure_service, self.benchmark_service)
        self.portfolio_proj_service = PortfolioProjectionService(self.pos_repo, self.cash_repo, self.portfolio_val_service)
        self.portfolio_api = PortfolioAPI(
            self.portfolio_proj_service, self.portfolio_val_service, self.val_repo, self.pos_repo, self.cash_repo
        )
        
        # Thesis Setup
        from karsa.thesis.api.router import thesis_router
        self.thesis_router = thesis_router
        
        # Memory / MinIO
        self.blob_storage = LocalBlobStorage("/tmp/minio")
        self.schema_repo = InMemorySchemaRepository()
        self.snapshot_repo = InMemorySnapshotRepository()
        self.registry_service = SchemaRegistryService(self.schema_repo)
        self.snapshot_service = SnapshotService(self.registry_service, self.snapshot_repo, self.blob_storage)

        # Data Bridge Setup (Sprint-51)
        from karsa.providers.application.credential_service import CredentialEncryptionService
        from karsa.providers.application.data_bridge_services import DataBridgeProviderService
        from karsa.providers.infrastructure.storage.data_bridge_repositories import (
            DataBridgeProviderRepository,
            ProviderHealthLogRepository,
        )
        self.data_bridge_provider_repo = DataBridgeProviderRepository(self.conn)
        self.data_bridge_health_repo = ProviderHealthLogRepository(self.conn)
        try:
            self.credential_service = CredentialEncryptionService()
        except Exception:
            self.credential_service = None  # Will be None if DATA_BRIDGE_MASTER_KEY not set
        self.data_bridge_service = DataBridgeProviderService(
            provider_repo=self.data_bridge_provider_repo,
            health_repo=self.data_bridge_health_repo,
            credential_service=self.credential_service,
            event_bus=self.event_bus,
        )

        # Sprint-53: Resilience Services
        from karsa.providers.application.health_monitor import HealthMonitorService
        from karsa.providers.application.failover_service import FailoverService
        from karsa.providers.application.gap_fill_service import GapFillService

        self.health_monitor = HealthMonitorService(
            health_repo=self.data_bridge_health_repo,
            provider_repo=self.data_bridge_provider_repo,
        )
        self.failover_service = FailoverService(
            provider_repo=self.data_bridge_provider_repo,
            health_repo=self.data_bridge_health_repo,
            credential_service=self.credential_service,
            event_bus=self.event_bus,
        )
        self.gap_fill_service = GapFillService(
            event_bus=self.event_bus,
        )

        # LLM Pool Config Setup (Sprint-54 prep)
        from karsa.llm.infrastructure.storage.config_repository import LLMConfigRepository
        from karsa.llm.application.config_service import LLMConfigService

        self.llm_config_repo = LLMConfigRepository(self.conn)
        self.llm_config_service = LLMConfigService(
            config_repo=self.llm_config_repo,
            credential_service=self.credential_service,
            event_bus=self.event_bus,
        ) if self.credential_service else None

        # Attribution Setup
        from karsa.attribution.infrastructure.repositories import AttributionRepository
        self.attribution_repo = AttributionRepository(self.conn)

        # Intelligence Setup
        from sqlalchemy import create_engine
        from karsa.firm_intelligence.repository.data_mart_repo import PostgresIntelligenceDataMartRepository
        from karsa.firm_intelligence.application.query_service import FirmIntelligenceQueryService

        db_name = os.environ.get("POSTGRES_DB", "karsa_db")
        db_user = os.environ.get("POSTGRES_USER", "karsa")
        db_pass = os.environ.get("POSTGRES_PASSWORD", "karsa_password")
        db_host = os.environ.get("POSTGRES_HOST", "postgres")
        db_port = os.environ.get("POSTGRES_PORT", "5432")
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

        self.sa_engine = create_engine(db_url)
        self.intelligence_mart_repo = PostgresIntelligenceDataMartRepository(self.sa_engine)
        self.intelligence_service = FirmIntelligenceQueryService(self.intelligence_mart_repo)

        # Allocation Setup (Sprint-06)
        from karsa.allocation.infrastructure.persistence.postgres_allocation_proposal_repository import PostgresAllocationProposalRepository
        from karsa.allocation.infrastructure.persistence.postgres_proposal_status_projection_repository import PostgresProposalStatusProjectionRepository
        from karsa.allocation.application.service.proportional_weighting_strategy import ProportionalWeightingStrategy
        from karsa.allocation.application.service.allocation_recommendation_service import AllocationRecommendationService

        self.proposal_repo = PostgresAllocationProposalRepository(self.conn)
        self.proposal_projection_repo = PostgresProposalStatusProjectionRepository(self.conn)
        self.weighting_strategy = ProportionalWeightingStrategy()
        self.allocation_recommendation_service = AllocationRecommendationService(
            proposal_repo=self.proposal_repo,
            weighting_strategy=self.weighting_strategy,
            intelligence_query_service=self.intelligence_service,
            event_publisher=self.event_bus,
        )

        # Update CIO service with proposal repos
        self.decision_service.proposal_repo = self.proposal_repo
        self.decision_service.projection_repo = self.proposal_projection_repo

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.pool.putconn(self.conn)
        if self.pool:
            self.pool.close()
