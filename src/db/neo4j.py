import os
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, query, parameters=None):
        if not self.driver:
            self.connect()
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []

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

    def connect_vendor(self, tenant_id, capability_name, vendor_name, product_name):
        """Deprecated: Use upsert_vendor_product for more flexibility."""
        return self.upsert_vendor_product(tenant_id, vendor_name, product_name, "Capability", capability_name)

    def save_proposal(self, tenant_id, query, content, proposal_id=None):
        """Saves a synthesized architectural proposal to the graph."""
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        if not proposal_id:
            import uuid
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

    def get_all_capabilities(self, tenant_id):
        """Retrieves all capabilities for a specific tenant."""
        cypher = """
        MATCH (c:Capability {tenant_id: $tenant_id})
        RETURN c.name as name, c.description as description, labels(c) as labels
        """
        return self.query(cypher, {"tenant_id": tenant_id})

    def get_proposal_by_id(self, tenant_id, proposal_id):
        """Retrieves the full content of a specific proposal for a specific tenant."""
        cypher = """
        MATCH (p:Proposal {id: $proposal_id, tenant_id: $tenant_id})
        RETURN p.id as id, p.query as query, p.content as content, p.timestamp as timestamp
        """
        results = self.query(cypher, {"proposal_id": proposal_id, "tenant_id": tenant_id})
        return results[0] if results else None

neo4j_client = Neo4jClient()
