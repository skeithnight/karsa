import uuid
from datetime import datetime, timezone
import json
from decimal import Decimal
import psycopg

from karsa.app import app
from karsa.bootstrap import get_postgres_pool
from karsa.portfolio.api import get_portfolio_api

from karsa.cio.domain.models import DecisionJournal
from karsa.cio.domain.events import CIODecisionApproved
from karsa.cio.application.services import CioApplicationService
from karsa.cio.repositories import PostgresCIODecisionRepository

from karsa.governance.domain.models import PostMortemRecord
from karsa.governance.application.services import PostMortemService
from karsa.governance.repositories import PostgresPostMortemRecordRepository, PostgresRecommendationRepository

def seed_portfolio():
    from karsa.bootstrap import container
    api = get_portfolio_api()
    # It requires PortfolioAPI which is provided by container.get_portfolio_api() ?
    # Let's see how app.py overrides it
