import datetime
import json
import os
import uuid
from typing import Any, Optional, Union
from neo4j import GraphDatabase, Driver
import logging

from src.db.vendor_canonical import canonical_vendor_name, normalize_vendor_input

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
        """Creates or updates a capability and links it to exactly one domain (removes other domain links)."""
        query = """
        MERGE (c:Capability {name: $name, tenant_id: $tenant_id})
        SET c.description = $description
        WITH c
        OPTIONAL MATCH (old_d:Domain {tenant_id: $tenant_id})-[r:HAS_CAPABILITY]->(c)
        DELETE r
        WITH c
        MERGE (d:Domain {name: $domain, tenant_id: $tenant_id})
        MERGE (d)-[:HAS_CAPABILITY]->(c)
        RETURN c
        """
        return self.query(query, {"domain": domain, "name": name, "description": description, "tenant_id": tenant_id})

    def apply_capability_registry_domain_links(
        self,
        tenant_id: str,
        registry: Union[dict, str],
        *,
        normalize_null_tenant_capabilities: bool = False,
    ) -> dict[str, Any]:
        """
        Batch-align (:Domain)-[:HAS_CAPABILITY]->(:Capability) from a Domain Steward-shaped registry JSON.
        Each entry uses owning_domain; reuses upsert_capability so only one domain link remains per capability per tenant.
        """
        if isinstance(registry, str):
            registry = json.loads(registry)
        caps = registry.get("capabilities")
        if not isinstance(caps, list):
            return {"applied": 0, "skipped": 0, "errors": ["registry.capabilities must be a list"]}

        applied = 0
        skipped = 0
        errors: list[str] = []

        for raw in caps:
            if not isinstance(raw, dict):
                skipped += 1
                continue
            name = raw.get("name")
            domain = raw.get("owning_domain")
            if not isinstance(name, str) or not name.strip():
                skipped += 1
                continue
            if not isinstance(domain, str) or not domain.strip():
                skipped += 1
                continue
            name = name.strip()
            domain = domain.strip()
            row_tid = raw.get("tenant_id")
            effective_tenant = (
                row_tid.strip()
                if isinstance(row_tid, str) and row_tid.strip()
                else tenant_id
            )

            if normalize_null_tenant_capabilities:
                try:
                    self.query(
                        """
                        MATCH (c:Capability {name: $name})
                        WHERE c.tenant_id IS NULL
                        SET c.tenant_id = $tenant_id
                        """,
                        {"name": name, "tenant_id": effective_tenant},
                    )
                except Exception as e:
                    errors.append(f"{name}: normalize null tenant failed: {e}")
                    continue

            desc = ""
            d = raw.get("description")
            if isinstance(d, str):
                desc = d

            try:
                self.upsert_capability(effective_tenant, domain, name, desc)
                applied += 1
            except Exception as e:
                errors.append(f"{name}: {e}")

        return {"applied": applied, "skipped": skipped, "errors": errors}

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

    def upsert_process(self, tenant_id, capability_name, process_name, process_description=""):
        """Creates a process node and links it to a capability."""
        query = """
        MERGE (c:Capability {name: $capability_name, tenant_id: $tenant_id})
        MERGE (p:Process {name: $process_name, tenant_id: $tenant_id})
        SET p.description = $process_description
        MERGE (p)-[:SUPPORTS_CAPABILITY]->(c)
        RETURN p
        """
        return self.query(query, {
            "capability_name": capability_name,
            "process_name": process_name,
            "process_description": process_description,
            "tenant_id": tenant_id
        })

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

    def resolve_vendor_display_name(self, vendor_name: Optional[str]) -> str:
        """
        Resolve LLM/raw vendor string to catalog display_name when seeded; else Python fallback aliases.
        """
        if not isinstance(vendor_name, str) or not vendor_name.strip():
            return vendor_name if isinstance(vendor_name, str) else ""
        n = normalize_vendor_input(vendor_name)
        try:
            rows = self.query(
                """
                MATCH (a:VendorCatalogAlias {normalized: $n})-[:RESOLVES_TO]->(e:VendorCatalogEntry)
                RETURN e.display_name AS dn
                LIMIT 1
                """,
                {"n": n},
            )
            if rows and rows[0].get("dn"):
                return str(rows[0]["dn"])
        except Exception as ex:
            logger.debug("Vendor catalog lookup failed, using fallback: %s", ex)
        return canonical_vendor_name(vendor_name)

    def ensure_vendor_subsidiary_rollup(self, tenant_id: str, resolved_vendor_display_name: str) -> None:
        """
        If this vendor is a catalog subsidiary, MERGE (:Vendor)-[:SUBSIDIARY_OF {legal_rollup:true}]->(parent :Vendor).
        Subsidiary keeps OFFERS; legal relationship is explicit for rollup reporting.
        """
        if not resolved_vendor_display_name or not tenant_id:
            return
        n = normalize_vendor_input(resolved_vendor_display_name)
        try:
            rows = self.query(
                """
                MATCH (a:VendorCatalogAlias {normalized: $n})-[:RESOLVES_TO]->(child:VendorCatalogEntry)
                OPTIONAL MATCH (child)-[:SUBSIDIARY_OF]->(parent:VendorCatalogEntry)
                RETURN child.display_name AS child_name, parent.display_name AS parent_name
                LIMIT 1
                """,
                {"n": n},
            )
        except Exception as ex:
            logger.debug("Subsidiary rollup skipped: %s", ex)
            return
        if not rows:
            return
        parent_name = rows[0].get("parent_name")
        child_name = rows[0].get("child_name")
        if not parent_name or not child_name:
            return
        self.query(
            """
            MERGE (cv:Vendor {tenant_id: $t, name: $child})
            MERGE (pv:Vendor {tenant_id: $t, name: $parent})
            MERGE (cv)-[r:SUBSIDIARY_OF]->(pv)
            SET r.legal_rollup = true
            """,
            {"t": tenant_id, "child": child_name, "parent": parent_name},
        )

    def seed_vendor_catalog(self) -> dict[str, Any]:
        """
        Global taxonomy: VendorCatalogEntry, VendorCatalogAlias-[:RESOLVES_TO], subsidiary SUBSIDIARY_OF.
        Idempotent. Safe to run on every deploy if desired.
        """
        from src.db.vendor_catalog_data import VENDOR_CATALOG_ENTRIES

        try:
            self.query(
                "CREATE CONSTRAINT vendor_catalog_entry_key IF NOT EXISTS "
                "FOR (e:VendorCatalogEntry) REQUIRE e.key IS UNIQUE",
                {},
            )
        except Exception as ex:
            logger.debug("Constraint vendor_catalog_entry_key: %s", ex)
        try:
            self.query(
                "CREATE CONSTRAINT vendor_catalog_alias_norm IF NOT EXISTS "
                "FOR (a:VendorCatalogAlias) REQUIRE a.normalized IS UNIQUE",
                {},
            )
        except Exception as ex:
            logger.debug("Constraint vendor_catalog_alias_norm: %s", ex)

        aliases_linked = 0
        for entry in VENDOR_CATALOG_ENTRIES:
            key = entry["key"]
            display_name = entry["display_name"]
            aliases = list(entry.get("aliases") or [])
            if display_name not in aliases:
                aliases.append(display_name)
            self.query(
                """
                MERGE (e:VendorCatalogEntry {key: $key})
                SET e.display_name = $display_name
                """,
                {"key": key, "display_name": display_name},
            )
            for al in aliases:
                if not isinstance(al, str) or not al.strip():
                    continue
                norm = normalize_vendor_input(al)
                self.query(
                    """
                    MERGE (a:VendorCatalogAlias {normalized: $norm})
                    MERGE (e:VendorCatalogEntry {key: $key})
                    MERGE (a)-[:RESOLVES_TO]->(e)
                    """,
                    {"norm": norm, "key": key},
                )
                aliases_linked += 1

        subs = 0
        for entry in VENDOR_CATALOG_ENTRIES:
            parent_key = entry.get("subsidiary_of")
            if not parent_key:
                continue
            self.query(
                """
                MATCH (child:VendorCatalogEntry {key: $ck})
                MATCH (parent:VendorCatalogEntry {key: $pk})
                MERGE (child)-[r:SUBSIDIARY_OF]->(parent)
                SET r.legal_rollup = true
                """,
                {"ck": entry["key"], "pk": parent_key},
            )
            subs += 1

        return {
            "entries": len(VENDOR_CATALOG_ENTRIES),
            "alias_nodes_touched": aliases_linked,
            "subsidiary_relationships": subs,
        }

    def upsert_vendor_product(self, tenant_id, vendor_name, product_name, fulfilling_entity_type, fulfilling_entity_name):
        """Connects a vendor and product to either a Capability, Application, or Technology."""
        v_resolved = self.resolve_vendor_display_name(vendor_name) if vendor_name else vendor_name
        query = f"""
        MERGE (v:Vendor {{name: $vendor_name, tenant_id: $tenant_id}})
        MERGE (p:Product {{name: $product_name, tenant_id: $tenant_id}})
        MERGE (v)-[:OFFERS]->(p)
        WITH p
        MATCH (e:{fulfilling_entity_type} {{name: $fulfilling_entity_name, tenant_id: $tenant_id}})
        MERGE (p)-[:IMPLEMENTS]->(e)
        RETURN p
        """
        out = self.query(
            query,
            {
                "vendor_name": v_resolved,
                "product_name": product_name,
                "fulfilling_entity_name": fulfilling_entity_name,
                "tenant_id": tenant_id,
            },
        )
        try:
            self.ensure_vendor_subsidiary_rollup(tenant_id, v_resolved)
        except Exception as ex:
            logger.warning("Could not set subsidiary rollup for %s: %s", v_resolved, ex)
        return out

    def get_vendor_capability_context(self, tenant_id: str, capability_names: list[str]) -> list[dict]:
        """
        Existing Vendor→Product links that IMPLEMENT (directly or via Application FULFILLS) the given capabilities.
        Used to steer agents away from duplicate vendor spellings.
        """
        if not capability_names:
            return []
        cypher = """
        MATCH (c:Capability {tenant_id: $tenant_id})
        WHERE c.name IN $cap_names
        MATCH (v:Vendor {tenant_id: $tenant_id})-[:OFFERS]->(p:Product {tenant_id: $tenant_id})
        WHERE (p)-[:IMPLEMENTS]->(c)
           OR EXISTS {
             MATCH (p)-[:IMPLEMENTS]->(a:Application {tenant_id: $tenant_id})-[:FULFILLS]->(c)
           }
        RETURN DISTINCT v.name AS vendor, p.name AS product, c.name AS capability
        ORDER BY capability, vendor, product
        """
        return self.query(
            cypher,
            {"tenant_id": tenant_id, "cap_names": list(capability_names)},
        )

    def merge_vendor_node_into(self, tenant_id: str, duplicate_name: str, keeper_name: str) -> None:
        """Re-point OFFERS from duplicate Vendor to keeper, then remove duplicate node."""
        if duplicate_name == keeper_name:
            return
        prods = self.query(
            """
            MATCH (dup:Vendor {tenant_id: $t, name: $dup})-[r:OFFERS]->(p:Product)
            RETURN p.name AS pname
            """,
            {"t": tenant_id, "dup": duplicate_name},
        )
        for row in prods:
            pname = row.get("pname")
            if not pname:
                continue
            self.query(
                """
                MATCH (keep:Vendor {tenant_id: $t, name: $keep})
                MATCH (p:Product {tenant_id: $t, name: $pn})
                MERGE (keep)-[:OFFERS]->(p)
                WITH p
                MATCH (dup:Vendor {tenant_id: $t, name: $dup})-[r:OFFERS]->(p)
                DELETE r
                """,
                {"t": tenant_id, "keep": keeper_name, "dup": duplicate_name, "pn": pname},
            )
        self.query(
            "MATCH (dup:Vendor {tenant_id: $t, name: $dup}) DETACH DELETE dup",
            {"t": tenant_id, "dup": duplicate_name},
        )

    def dedupe_vendors_for_tenant(self, tenant_id: str) -> dict[str, Any]:
        """Merge Vendor nodes that map to the same canonical name; preserves Product and IMPLEMENTS."""
        from collections import defaultdict

        rows = self.query(
            "MATCH (v:Vendor {tenant_id: $t}) RETURN DISTINCT v.name AS n ORDER BY n",
            {"t": tenant_id},
        )
        names = [r["n"] for r in rows if r.get("n")]
        groups: dict[str, list[str]] = defaultdict(list)
        for n in names:
            key = self.resolve_vendor_display_name(n)
            groups[key].append(n)
        removed = 0
        for canonical, variants in groups.items():
            uniq = sorted(set(variants))
            if len(uniq) <= 1:
                continue
            if canonical in uniq:
                keep = canonical
            else:
                keep = sorted(uniq, key=lambda x: (-len(x), x.lower()))[0]
            for dup in uniq:
                if dup == keep:
                    continue
                self.merge_vendor_node_into(tenant_id, dup, keep)
                removed += 1
        return {"tenant_id": tenant_id, "vendor_nodes_merged": removed, "groups_considered": len(groups)}

    def dedupe_vendors_all_tenants(self) -> list[dict[str, Any]]:
        rows = self.query(
            "MATCH (v:Vendor) WHERE v.tenant_id IS NOT NULL RETURN DISTINCT v.tenant_id AS t ORDER BY t",
            {},
        )
        out: list[dict[str, Any]] = []
        for r in rows:
            tid = r.get("t")
            if tid:
                out.append(self.dedupe_vendors_for_tenant(tid))
        return out

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

    def get_capabilities_with_domains_for_tenant(self, tenant_id: str):
        """Capabilities linked to domains via HAS_CAPABILITY, with optional PARENT_OF parent name."""
        cypher = """
        MATCH (d:Domain {tenant_id: $tenant_id})-[:HAS_CAPABILITY]->(c:Capability {tenant_id: $tenant_id})
        OPTIONAL MATCH (parent:Capability {tenant_id: $tenant_id})-[:PARENT_OF]->(c)
        RETURN d.name AS domain, c.name AS name,
               coalesce(c.description, '') AS description,
               parent.name AS parent_name
        ORDER BY d.name, toLower(c.name)
        """
        return self.query(cypher, {"tenant_id": tenant_id})

    def get_user_by_email(self, email):
        """Retrieves a user by their email address (exact match)."""
        cypher = "MATCH (u:User {email: $email}) RETURN u"
        results = self.query(cypher, {"email": email})
        return results[0]["u"] if results else None

    def find_user_for_login(self, normalized_email: str):
        """
        Match login identifier case-insensitively (legacy rows may have mixed-case email).
        normalized_email must already be lowercased/stripped.
        """
        cypher = """
        MATCH (u:User)
        WHERE toLower(trim(u.email)) = $norm
        RETURN u
        """
        results = self.query(cypher, {"norm": normalized_email})
        if len(results) > 1:
            return None
        return results[0]["u"] if results else None

    def safe_canonicalize_stored_email(self, current_stored: str, canonical: str) -> None:
        """If stored casing differs from canonical and canonical is not taken by another user, update."""
        if not current_stored or not canonical or current_stored == canonical:
            return
        if self.count_users_by_email(canonical) > 0:
            return
        self.update_user_login_email(current_stored, canonical)

    def count_users_by_email(self, email: str) -> int:
        cypher = "MATCH (u:User {email: $email}) RETURN count(u) AS c"
        results = self.query(cypher, {"email": email})
        if not results:
            return 0
        c = results[0].get("c")
        return int(c) if c is not None else 0

    def update_user_full_name(self, email: str, full_name: str):
        cypher = """
        MATCH (u:User {email: $email})
        SET u.full_name = $full_name
        RETURN u.email AS email
        """
        return self.query(cypher, {"email": email, "full_name": full_name})

    def update_user_login_email(self, old_email: str, new_email: str):
        """Change primary login email; caller must ensure new_email is normalized and unused."""
        cypher = """
        MATCH (u:User {email: $old_email})
        SET u.email = $new_email
        RETURN u.email AS email
        """
        return self.query(cypher, {"old_email": old_email, "new_email": new_email})

    def update_user_password_hash(self, email: str, hashed_password: str):
        cypher = """
        MATCH (u:User {email: $email})
        SET u.password = $hashed_password
        RETURN u.email AS email
        """
        return self.query(cypher, {"email": email, "hashed_password": hashed_password})

    def create_user(
        self,
        email,
        hashed_password,
        full_name,
        tenant_id,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        openai_base_url: Optional[str] = None,
    ):
        """Creates a new user and links them to a tenant."""
        cypher = """
        MERGE (t:Tenant {id: $tenant_id})
        MERGE (u:User {email: $email})
        SET u.password = $hashed_password,
            u.full_name = $full_name,
            u.tenant_id = $tenant_id,
            u.llm_model = $llm_model,
            u.llm_provider = $llm_provider,
            u.openai_base_url = $openai_base_url,
            u.created_at = datetime()
        MERGE (u)-[:MEMBER_OF]->(t)
        RETURN u.email as email
        """
        return self.query(cypher, {
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "tenant_id": tenant_id,
            "llm_model": llm_model or "gpt-4o",
            "llm_provider": llm_provider or "openai",
            "openai_base_url": openai_base_url,
        })

    def get_user_llm_model(self, email: str) -> Optional[str]:
        """Returns stored llm_model or None if user missing."""
        cypher = "MATCH (u:User {email: $email}) RETURN u.llm_model as llm_model"
        results = self.query(cypher, {"email": email})
        if not results:
            return None
        return results[0].get("llm_model")

    def get_user_llm_settings(self, email: str) -> Optional[dict]:
        """Returns llm_provider, openai_base_url, llm_model or None if user missing."""
        cypher = """
        MATCH (u:User {email: $email})
        RETURN coalesce(u.llm_provider, 'openai') AS llm_provider,
               u.openai_base_url AS openai_base_url,
               u.llm_model AS llm_model
        """
        results = self.query(cypher, {"email": email})
        if not results:
            return None
        row = results[0]
        return {
            "llm_provider": row.get("llm_provider") or "openai",
            "openai_base_url": row.get("openai_base_url"),
            "llm_model": row.get("llm_model"),
        }

    def set_user_llm_model(self, email: str, llm_model: str):
        """Persist preferred OpenAI chat model id on the user."""
        cypher = """
        MATCH (u:User {email: $email})
        SET u.llm_model = $llm_model
        RETURN u.email as email
        """
        return self.query(cypher, {"email": email, "llm_model": llm_model})

    def set_user_llm_settings(
        self,
        email: str,
        llm_provider: str,
        llm_model: str,
        openai_base_url: Optional[str],
    ):
        """Persist LLM backend, model id, and optional OpenAI-compatible base URL."""
        cypher = """
        MATCH (u:User {email: $email})
        SET u.llm_provider = $llm_provider,
            u.llm_model = $llm_model,
            u.openai_base_url = $openai_base_url
        RETURN u.email as email
        """
        return self.query(
            cypher,
            {
                "email": email,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "openai_base_url": openai_base_url,
            },
        )

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
