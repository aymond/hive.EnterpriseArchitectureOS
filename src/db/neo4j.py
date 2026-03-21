import datetime
import os
import uuid
from typing import Optional
from neo4j import GraphDatabase, Driver
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            driver = self.driver
            if driver is not None:
                driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    def close(self):
        driver = self.driver
        if driver is not None:
            driver.close()

    def query(self, query, parameters=None):
        if not self.driver:
            self.connect()
        if not self.driver:
            raise ConnectionError("Neo4j driver is not connected. Check NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD.")
        try:
            with self.driver.session() as session:  # type: ignore[union-attr]
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    def upsert_capability(self, tenant_id, domain, name, description):
        """Creates or updates a capability node and links it to a domain."""
        query = """
        MERGE (d:Domain {name: $domain, tenant_id: $tenant_id})
        MERGE (c:Capability {name: $name, tenant_id: $tenant_id})
        SET c.description = $description
        MERGE (d)-[:HAS_CAPABILITY]->(c)
        RETURN c
        """
        return self.query(query, {"domain": domain, "name": name, "description": description, "tenant_id": tenant_id})

    def set_capability_parent(self, tenant_id, parent_name, child_name):
        """Links a child capability to a parent capability via PARENT_OF."""
        query = """
        MATCH (p:Capability {name: $parent_name, tenant_id: $tenant_id})
        MATCH (c:Capability {name: $child_name, tenant_id: $tenant_id})
        MERGE (p)-[:PARENT_OF]->(c)
        RETURN p, c
        """
        return self.query(query, {"parent_name": parent_name, "child_name": child_name, "tenant_id": tenant_id})

    def get_capability_hierarchy(self, tenant_id, capability_names):
        """
        Retrieves the hierarchy for a set of capabilities, including their parents and children.
        """
        query = """
        MATCH (c:Capability {tenant_id: $tenant_id})
        WHERE c.name IN $capability_names
        OPTIONAL MATCH (p:Capability {tenant_id: $tenant_id})-[r:PARENT_OF]->(c)
        OPTIONAL MATCH (c)-[r2:PARENT_OF]->(child:Capability {tenant_id: $tenant_id})
        RETURN p.name as parent, c.name as capability, child.name as child
        """
        return self.query(query, {"capability_names": capability_names, "tenant_id": tenant_id})

    def upsert_application(self, tenant_id, capability_name, app_name, app_description=""):
        """Creates an application node and links it to a capability."""
        query = """
        MERGE (c:Capability {name: $capability_name, tenant_id: $tenant_id})
        MERGE (a:Application {name: $app_name, tenant_id: $tenant_id})
        SET a.description = $app_description
        MERGE (a)-[:FULFILLS]->(c)
        RETURN a
        """
        return self.query(query, {"capability_name": capability_name, "app_name": app_name, "app_description": app_description, "tenant_id": tenant_id})

    def upsert_technology(self, tenant_id, app_name, tech_name, tech_category=""):
        """Creates a technology node and links it to an application."""
        query = """
        MERGE (a:Application {name: $app_name, tenant_id: $tenant_id})
        MERGE (t:Technology {name: $tech_name, tenant_id: $tenant_id})
        SET t.category = $tech_category
        MERGE (a)-[:RUNS_ON]->(t)
        RETURN t
        """
        return self.query(query, {"app_name": app_name, "tech_name": tech_name, "tech_category": tech_category, "tenant_id": tenant_id})

    def upsert_vendor_product(self, tenant_id, vendor_name, product_name, fulfilling_entity_type, fulfilling_entity_name):
        """Connects a vendor and product to either a Capability, Application, or Technology."""
        query = f"""
        MERGE (v:Vendor {{name: $vendor_name, tenant_id: $tenant_id}})
        MERGE (p:Product {{name: $product_name, tenant_id: $tenant_id}})
        MERGE (v)-[:OFFERS]->(p)
        WITH p
        MATCH (e:{fulfilling_entity_type} {{name: $fulfilling_entity_name, tenant_id: $tenant_id}})
        MERGE (p)-[:IMPLEMENTS]->(e)
        RETURN p
        """
        return self.query(query, {
            "vendor_name": vendor_name,
            "product_name": product_name,
            "fulfilling_entity_name": fulfilling_entity_name,
            "tenant_id": tenant_id
        })

    def save_proposal(self, tenant_id, query, content, proposal_id=None):
        """Saves a synthesized architectural proposal to the graph."""
        timestamp = datetime.datetime.now().isoformat()
        if not proposal_id:
            proposal_id = str(uuid.uuid4())
            
        cypher = """
        MERGE (p:Proposal {id: $proposal_id})
        SET p.query = $query,
            p.content = $content,
            p.timestamp = $timestamp,
            p.tenant_id = $tenant_id
        RETURN p.id as id
        """
        return self.query(cypher, {
            "proposal_id": proposal_id,
            "query": query,
            "content": content,
            "timestamp": timestamp,
            "tenant_id": tenant_id
        })

    def get_proposals(self, tenant_id):
        """Retrieves a list of all saved proposals for a specific tenant."""
        cypher = """
        MATCH (p:Proposal {tenant_id: $tenant_id})
        RETURN p.id as id, p.query as query, p.timestamp as timestamp
        ORDER BY p.timestamp DESC
        """
        return self.query(cypher, {"tenant_id": tenant_id})
    def get_proposal_by_id(self, tenant_id, proposal_id):
        """Retrieves a specific proposal by ID for a specific tenant."""
        cypher = """
        MATCH (p:Proposal {id: $proposal_id, tenant_id: $tenant_id})
        RETURN p.id as id, p.query as query, p.content as content, p.timestamp as timestamp
        """
        results = self.query(cypher, {"proposal_id": proposal_id, "tenant_id": tenant_id})
        return results[0] if results else None


    def get_all_capabilities(self, tenant_id):
        """Retrieves all capabilities for a specific tenant."""
        cypher = """
        MATCH (c:Capability {tenant_id: $tenant_id})
        RETURN c.name as name, c.description as description, labels(c) as labels
        """
        return self.query(cypher, {"tenant_id": tenant_id})

    def get_user_by_email(self, email):
        """Retrieves a user by their email address."""
        cypher = "MATCH (u:User {email: $email}) RETURN u"
        results = self.query(cypher, {"email": email})
        return results[0]["u"] if results else None

    def create_user(self, email, hashed_password, full_name, tenant_id):
        """Creates a new user and links them to a tenant."""
        cypher = """
        MERGE (t:Tenant {id: $tenant_id})
        MERGE (u:User {email: $email})
        SET u.password = $hashed_password,
            u.full_name = $full_name,
            u.tenant_id = $tenant_id,
            u.created_at = datetime()
        MERGE (u)-[:MEMBER_OF]->(t)
        RETURN u.email as email
        """
    def update_user_api_keys(self, email: str, encrypted_openai: Optional[str] = None, encrypted_tavily: Optional[str] = None):
        """Stores the symmetrically encrypted API keys on the User node."""
        sets = []
        params = {"email": email}
        if encrypted_openai is not None:
            sets.append("u.encrypted_openai_key = $encrypted_openai")
            params["encrypted_openai"] = encrypted_openai
        if encrypted_tavily is not None:
            sets.append("u.encrypted_tavily_key = $encrypted_tavily")
            params["encrypted_tavily"] = encrypted_tavily
            
        if not sets:
            return None
            
        set_clause = ", ".join(sets)
        cypher = f"""
        MATCH (u:User {{email: $email}})
        SET {set_clause}
        RETURN u.email as email
        """
        return self.query(cypher, params)

    def get_user_api_keys(self, email: str) -> dict:
        """Retrieves the symmetrically encrypted API keys from the User node."""
        cypher = """
        MATCH (u:User {email: $email})
        RETURN u.encrypted_openai_key as openai, u.encrypted_tavily_key as tavily
        """
        results = self.query(cypher, {"email": email})
        if results:
            return {
                "openai": results[0].get("openai"),
                "tavily": results[0].get("tavily")
            }
        return {"openai": None, "tavily": None}

    def get_tenant_by_id(self, tenant_id):
        """Retrieves tenant details."""
        cypher = "MATCH (t:Tenant {id: $tenant_id}) RETURN t"
        results = self.query(cypher, {"tenant_id": tenant_id})
        return results[0]["t"] if results else None

neo4j_client = Neo4jClient()
