import traceback
import sys
from karsa.bootstrap import ApplicationContainer

try:
    c = ApplicationContainer()
    val = c.portfolio_api.get_valuation('PORT-MAIN')
    print(val)
except Exception as e:
    traceback.print_exc()
