# locustfile.py
from locust import HttpUser, task, between, events
import random
import json

# IDs and codes that your Python scripts generated.
# It's better if your API can provide lists of these for Locust to use dynamically.
# For now, we'll use ranges and examples based on our generation.

# Based on 04_insert_users.sql (scaled)
MAX_USER_ID_LOCUST = 25000
# Based on 09_insert_stations.sql
STATION_CODES_SAMPLE_LOCUST = ["P01", "P02", "TC01", "A01", "B02", "ZP0100A01", "ZP0200B02"] # Add more real or generated station codes
# Based on 12_insert_routes.sql
ROUTE_CODES_SAMPLE_LOCUST = ["M25", "C96", "DM81", "T11", "BH907", "A11", "TC1"] # Add more real or generated route codes

# If you implement endpoints to get these lists, it would be ideal
# Example: /api/v1/users/ids, /api/v1/stations/codes, /api/v1/routes/codes

# Global variables to store data retrieved in on_start
ALL_ROUTE_CODES = []
ALL_STATION_IDENTIFIERS = [] # List of dicts: [{"code": "P01", "name": "Portal Américas"}, ...]


@events.init_command_line_parser.add_listener
def _(parser):
    parser.add_argument("--api-base-url", type=str, default="http://localhost:8000", help="Base URL of the API")

class SITPUser(HttpUser):
    # Virtual users will wait between 1 and 3 seconds between tasks
    wait_time = between(1, 3)
    host = "" # Will be set from command line or in on_start

    def on_start(self):
        """
        Called when a Locust user starts.
        Ideal for getting initial data that the user will use in their tasks.
        """
        self.host = self.environment.parsed_options.api_base_url
        print(f"Locust user starting, targeting host: {self.host}")

        # Populate global lists of routes and stations if they are empty
        # This is done once per Locust process, not per user, thanks to the ALL_ROUTE_CODES check
        # For distribution among workers, each worker would do this once.
        # Note: In a distributed Locust environment, each worker might do this.
        # You could have the master do this and distribute it, or have each worker load it.
        # For simplicity here, each worker would load it if the list is empty.
        
        global ALL_ROUTE_CODES
        if not ALL_ROUTE_CODES:
            try:
                response = self.client.get("/api/v1/routes/codes")
                response.raise_for_status() # Raises an exception for HTTP errors
                data = response.json()
                ALL_ROUTE_CODES = data.get("route_codes", [])
                if not ALL_ROUTE_CODES:
                    print("Warning: Received empty list of route codes from API, using hardcoded samples.")
                    ALL_ROUTE_CODES = ROUTE_CODES_SAMPLE_LOCUST
                else:
                    print(f"Successfully loaded {len(ALL_ROUTE_CODES)} route codes.")
            except Exception as e:
                print(f"Error fetching route codes in on_start: {e}. Using hardcoded samples.")
                ALL_ROUTE_CODES = ROUTE_CODES_SAMPLE_LOCUST
        
        global ALL_STATION_IDENTIFIERS
        if not ALL_STATION_IDENTIFIERS:
            try:
                response = self.client.get("/api/v1/stations/identifiers")
                response.raise_for_status()
                data = response.json()
                ALL_STATION_IDENTIFIERS = data.get("stations", [])
                if not ALL_STATION_IDENTIFIERS:
                    print("Warning: Received empty list of station identifiers from API, using hardcoded samples.")
                    ALL_STATION_IDENTIFIERS = [{"code": sc, "name": f"Station {sc}"} for sc in STATION_CODES_SAMPLE_LOCUST]
                else:
                    print(f"Successfully loaded {len(ALL_STATION_IDENTIFIERS)} station identifiers.")
            except Exception as e:
                print(f"Error fetching station identifiers in on_start: {e}. Using hardcoded samples.")
                ALL_STATION_IDENTIFIERS = [{"code": sc, "name": f"Station {sc}"} for sc in STATION_CODES_SAMPLE_LOCUST]


    @task(1) # Low frequency
    def ping_db(self):
        self.client.get("/ping-db")

    @task(3) # Medium frequency
    def get_users_count(self):
        self.client.get("/api/v1/users/count")

    @task(2) # Medium frequency - now implemented with Redis cache
    def get_active_users_count(self):
        self.client.get("/api/v1/users/active/count")

    @task(1)
    def get_latest_user(self):
        self.client.get("/api/v1/users/latest")

    @task(5) # High frequency
    def get_total_trips(self):
        self.client.get("/api/v1/trips/total", name="/trips/total (cached)") # Name for grouping in stats

    @task(3)
    def get_total_revenue(self):
        self.client.get("/api/v1/finance/revenue", name="/finance/revenue (cached)")

    @task(2) # Now available with proper caching
    def get_revenue_by_localities(self):
        self.client.get("/api/v1/finance/revenue/localities", name="/finance/revenue/localities (cached)")
    
    @task(2)
    def get_total_trips_by_localities(self):
        self.client.get("/api/v1/trips/total/localities", name="/trips/total/localities (cached)")

    @task(10) # Users frequently query this
    def get_realtime_arrivals(self):
        if ALL_STATION_IDENTIFIERS:
            station_code = random.choice(ALL_STATION_IDENTIFIERS)["code"]
            # The original endpoint was /stations/{station_id}/realtime-arrivals.
            # We'll assume your API now uses station_code or you have a mapping.
            # If the endpoint expects a numeric ID and you only have codes, you'll need an endpoint
            # that maps code to ID, or the endpoint accepts codes.
            # For now, I'll assume you can have an endpoint that accepts station_code
            # or that you can get the station_id somehow.
            # Here I'll use the station_code as if the endpoint accepted it.
            self.client.get(f"/stations/{station_code}/realtime-arrivals", name="/stations/[station_code]/realtime-arrivals")
        else:
            # Fallback if no station codes loaded
            self.client.get(f"/stations/{random.choice(STATION_CODES_SAMPLE_LOCUST)}/realtime-arrivals", name="/stations/[station_code]/realtime-arrivals")


    @task(8) # Also frequent
    def get_route_current_location(self):
        if ALL_ROUTE_CODES:
            route_code = random.choice(ALL_ROUTE_CODES)
            # Similar to the previous one, the original endpoint was /route/{route_id}/...
            # I'll assume the endpoint can take route_code.
            self.client.get(f"/route/{route_code}/current-location", name="/route/[route_code]/current-location")
        else:
            self.client.get(f"/route/{random.choice(ROUTE_CODES_SAMPLE_LOCUST)}/current-location", name="/route/[route_code]/current-location")


    @task(2)
    def get_system_alerts(self):
        self.client.get("/system/alerts")

    @task(5)
    def get_user_card_balance(self):
        user_id = random.randint(1, MAX_USER_ID_LOCUST)
        self.client.get(f"/users/{user_id}/card-balance", name="/users/[user_id]/card-balance")

    @task(4)
    def get_route_details(self):
        if ALL_ROUTE_CODES:
            route_code = random.choice(ALL_ROUTE_CODES)
            self.client.get(f"/api/v1/routes/{route_code}/details", name="/api/v1/routes/[route_code]/details")
        else:
            self.client.get(f"/api/v1/routes/{random.choice(ROUTE_CODES_SAMPLE_LOCUST)}/details", name="/api/v1/routes/[route_code]/details")


    @task(4)
    def get_station_details(self):
        if ALL_STATION_IDENTIFIERS:
            station_code = random.choice(ALL_STATION_IDENTIFIERS)["code"]
            self.client.get(f"/api/v1/stations/{station_code}/details", name="/api/v1/stations/[station_code]/details")
        else:
            self.client.get(f"/api/v1/stations/{random.choice(STATION_CODES_SAMPLE_LOCUST)}/details", name="/api/v1/stations/[station_code]/details")


    # --- WRITE TASKS (EXAMPLES - You need to implement these endpoints in your API) ---
    # These tasks would simulate the main transactional load in a real system.

    # @task(15) # Simulating a trip should be a very frequent action
    # def simulate_trip(self):
    #     # This task is the most complex to simulate realistically.
    #     # 1. Choose a card (card_id)
    #     # 2. Choose a route (route_id or route_code)
    #     # 3. Choose boarding station (from the route stops)
    #     # 4. Choose alighting station (after boarding station on the same route)
    #     # 5. Simulate times
    #     # 6. Your API would need an endpoint (e.g. POST /trips or POST /journeys) that:
    #     #    - Verifies card balance.
    #     #    - Calculates and deducts fare.
    #     #    - Creates record in `trips` table.
    #     #    - Potentially handles transfers.
    #
    #     card_id = random.randint(1, MAX_CARD_ID_LOCUST) # Preferably use active card IDs
    #     route_code = random.choice(ALL_ROUTE_CODES) if ALL_ROUTE_CODES else random.choice(ROUTE_CODES_SAMPLE_LOCUST)
    #     
    #     # Simplified logic for trip data
    #     trip_data = {
    #         "card_id": card_id,
    #         "route_code": route_code, 
    #         # Your API would need more details for boarding/alighting station,
    #         # or you could send a trip "type" and the API selects details.
    #         "boarding_station_code": random.choice(ALL_STATION_IDENTIFIERS)["code"] if ALL_STATION_IDENTIFIERS else random.choice(STATION_CODES_SAMPLE_LOCUST),
    #         "simulated_duration_minutes": random.randint(5, 45) 
    #     }
    #     # self.client.post("/api/v1/journeys/simulate", json=trip_data, name="/api/v1/journeys/simulate (WRITE)")
    #     pass # Implement POST call when you have the endpoint

    # @task(2) # Recharge a card
    # def simulate_recharge(self):
    #     card_id = random.randint(1, MAX_CARD_ID_LOCUST)
    #     amount = random.choice([5000, 10000, 20000, 50000])
    #     recharge_point_id = random.randint(1, 500) # Assuming you have up to 500 recharge_points
    #
    #     recharge_data = {
    #         "amount": amount,
    #         "recharge_point_id": recharge_point_id 
    #         # Your API might identify the card by path parameter or in the body
    #     }
    #     # self.client.post(f"/api/v1/cards/{card_id}/recharge", json=recharge_data, name="/api/v1/cards/[card_id]/recharge (WRITE)")
    #     pass # Implement POST call

# To run Locust:
# 1. Save this file as locustfile.py in the root of your project.
# 2. Open your terminal in the project root.
# 3. Run: locust -f locustfile.py --api-base-url http://localhost:8000
#    (Replace http://localhost:8000 with your API's base URL if different)
# 4. Open your browser and go to http://localhost:8089 (Locust's default web UI port).
# 5. Enter the total number of users to simulate and spawn rate (users per second).
# 6. Start the test.