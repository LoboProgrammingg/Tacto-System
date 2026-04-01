"""
Tacto Menu Provider Implementation.

Implements the MenuProvider port using Tacto External API.
Includes caching via Redis for performance.
"""

from datetime import datetime, timezone
from typing import Callable, Optional

import structlog

from tacto.config import get_settings
from tacto.application.ports.menu_provider import (
    InstitutionalData,
    MenuData,
    MenuItem,
    MenuProvider,
)
from tacto.shared.application import Err, Failure, Ok, Success
from tacto.shared.domain.value_objects import RestaurantId
from tacto.infrastructure.external.tacto_client import TactoClient
from tacto.infrastructure.redis.redis_client import RedisClient


logger = structlog.get_logger()


class TactoMenuProvider(MenuProvider):
    """
    Tacto API implementation of MenuProvider.

    Fetches menu and institutional data from Tacto External API (rag-full).
    Caches results in Redis for performance.

    The `empresa_resolver` must return a tuple (empresa_base_id, grupo_empresarial)
    for a given restaurant_id — both are required by the Tacto API.
    """

    def __init__(
        self,
        tacto_client: TactoClient,
        redis_client: Optional[RedisClient] = None,
        empresa_resolver: Optional[Callable] = None,
    ) -> None:
        """
        Args:
            tacto_client: Tacto API client
            redis_client: Optional Redis client for caching
            empresa_resolver: Async callable that receives restaurant_id and returns
                              (empresa_base_id: str, grupo_empresarial: str)
        """
        _settings = get_settings().tacto
        self._tacto = tacto_client
        self._redis = redis_client
        self._empresa_resolver = empresa_resolver
        self._menu_cache_ttl = _settings.menu_cache_ttl
        self._institutional_cache_ttl = _settings.institutional_cache_ttl

    def _cache_key(self, prefix: str, restaurant_id: RestaurantId) -> str:
        return f"tacto:{prefix}:{restaurant_id.value}"

    async def _get_cached(self, key: str) -> Optional[dict]:
        if not self._redis or not self._redis.is_connected:
            return None
        try:
            result = await self._redis.get_json(key)
            if isinstance(result, Success) and result.value:
                return result.value
        except Exception:
            pass
        return None

    async def _set_cached(self, key: str, data: dict, ttl: int) -> None:
        if not self._redis or not self._redis.is_connected:
            return
        try:
            await self._redis.set_json(key, data, ttl)
        except Exception:
            pass

    async def _resolve_empresa(
        self,
        restaurant_id: RestaurantId,
        empresa_base_id: Optional[str],
        grupo_empresarial: Optional[str],
    ) -> Success[tuple[str, str]] | Failure[Exception]:
        """Resolve empresa_base_id and grupo_empresarial, using resolver if needed."""
        if empresa_base_id and grupo_empresarial:
            return Ok((empresa_base_id, grupo_empresarial))

        if self._empresa_resolver:
            resolved = await self._empresa_resolver(restaurant_id)
            if isinstance(resolved, tuple) and len(resolved) == 2:
                return Ok(resolved)
            return Err(ValueError(f"empresa_resolver returned unexpected value: {resolved}"))

        return Err(ValueError("empresa_base_id and grupo_empresarial are required"))

    async def get_menu(
        self,
        restaurant_id: RestaurantId,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[MenuData] | Failure[Exception]:
        """
        Get menu data for a restaurant via Tacto RAG full endpoint.

        First checks Redis cache, then fetches from API.
        """
        cache_key = self._cache_key("menu", restaurant_id)
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug("Menu cache hit", restaurant_id=str(restaurant_id.value))
            return Ok(self._parse_menu_data(restaurant_id, cached))

        resolved = await self._resolve_empresa(restaurant_id, empresa_base_id, grupo_empresarial)
        if isinstance(resolved, Failure):
            return resolved

        emp_id, grupo = resolved.value
        result = await self._tacto.get_rag_full(grupo_empresarial=grupo, empresa_base_id=emp_id)

        if isinstance(result, Failure):
            logger.error(
                "Failed to fetch menu from Tacto",
                restaurant_id=str(restaurant_id.value),
                error=str(result.error),
            )
            return result

        raw = result.value
        logger.info(
            "tacto_rag_raw_response",
            restaurant_id=str(restaurant_id.value),
            keys=list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__,
            sample=str(raw)[:500],
        )
        await self._set_cached(cache_key, raw, self._menu_cache_ttl)
        return Ok(self._parse_menu_data(restaurant_id, raw))

    async def get_institutional_data(
        self,
        restaurant_id: RestaurantId,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[InstitutionalData] | Failure[Exception]:
        """
        Get institutional data for a restaurant.

        First checks Redis cache, then fetches from API.
        """
        cache_key = self._cache_key("institutional", restaurant_id)
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug("Institutional cache hit", restaurant_id=str(restaurant_id.value))
            return Ok(self._parse_institutional_data(restaurant_id, cached))

        resolved = await self._resolve_empresa(restaurant_id, empresa_base_id, grupo_empresarial)
        if isinstance(resolved, Failure):
            return resolved

        emp_id, grupo = resolved.value
        result = await self._tacto.get_institutional_data(
            grupo_empresarial=grupo, empresa_base_id=emp_id
        )

        if isinstance(result, Failure):
            logger.error(
                "Failed to fetch institutional data from Tacto",
                restaurant_id=str(restaurant_id.value),
                error=str(result.error),
            )
            return result

        await self._set_cached(cache_key, result.value, self._institutional_cache_ttl)
        return Ok(self._parse_institutional_data(restaurant_id, result.value))

    async def search_menu(
        self,
        restaurant_id: RestaurantId,
        query: str,
        limit: int = 5,
    ) -> Success[list[MenuItem]] | Failure[Exception]:
        """Search menu items by text query."""
        menu_result = await self.get_menu(restaurant_id)
        if isinstance(menu_result, Failure):
            return menu_result

        query_lower = query.lower()
        matching: list[MenuItem] = []

        for item in menu_result.value.items:
            if not item.is_available:
                continue
            if (
                query_lower in item.name.lower()
                or (item.description and query_lower in item.description.lower())
                or query_lower in item.category.lower()
            ):
                matching.append(item)
                if len(matching) >= limit:
                    break

        return Ok(matching)

    # ------------------------------------------------------------------ #
    # Parsing helpers                                                       #
    # ------------------------------------------------------------------ #

    def _parse_menu_data(self, restaurant_id: RestaurantId, data: dict) -> MenuData:
        """Parse Tacto rag-full response into MenuData.

        Tacto returns items with:
          - nomeCompleto  (product name)
          - textoInformativo (description)
          - tamanhos[0].preco (price — nested in sizes)
          - grupo  (group/category name)
          - variacoes (optional variants with prices)
        """
        items: list[MenuItem] = []
        categories: set[str] = set()

        cardapio = data.get("cardapio", data.get("itens", data.get("items", [])))

        for item_data in cardapio:
            # Category: prefer group name, fallback to categoria field
            category = item_data.get("grupo") or item_data.get("categoria") or "Outros"
            categories.add(category)

            # Price: extract from tamanhos list or variacoes
            price = self._extract_price(item_data)

            # Name: Tacto uses nomeCompleto, fallback to nome/name
            name = (
                item_data.get("nomeCompleto")
                or item_data.get("nome")
                or item_data.get("name")
                or ""
            )

            # Description: Tacto uses textoInformativo
            description = (
                item_data.get("textoInformativo")
                or item_data.get("descricao")
                or item_data.get("description")
            )

            items.append(
                MenuItem(
                    name=name,
                    description=description or None,
                    price=price,
                    category=category,
                    is_available=item_data.get("disponivel", item_data.get("available", True)),
                )
            )

        sorted_categories = sorted(categories)
        return MenuData(
            restaurant_id=restaurant_id,
            items=items,
            categories=sorted_categories,
            raw_text=self._build_menu_text(items, sorted_categories),
            last_updated=datetime.now(timezone.utc).isoformat(),
            address=self._extract_address(data),
            hours_text=self._extract_hours_text(data),
            opening_hours=self._extract_opening_hours_dict(data),
            restaurant_description=data.get("atividadesServicos") or data.get("nossaHistoria") or "",
        )

    def _parse_institutional_data(
        self, restaurant_id: RestaurantId, data: dict
    ) -> InstitutionalData:
        """Parse Tacto institutional response into InstitutionalData.

        Tacto uses: nome, horarioAtendimentoDelivery, formasPagamento/formas_pagamento
        """
        payment_methods = (
            data.get("formasPagamento")
            or data.get("formas_pagamento")
            or data.get("payment_methods")
            or []
        )
        if isinstance(payment_methods, str):
            payment_methods = [p.strip() for p in payment_methods.split(",")]

        return InstitutionalData(
            restaurant_id=restaurant_id,
            name=data.get("nome", data.get("name", "")),
            address=data.get("endereco", data.get("address")),
            phone=data.get("telefone", data.get("phone")),
            payment_methods=payment_methods,
            delivery_info=data.get("info_entrega", data.get("delivery_info")),
            raw_text=self._build_institutional_text(data),
        )

    def _extract_price(self, item_data: dict) -> float:
        """Extract price from Tacto item — checks tamanhos, variacoes, then flat price."""
        tamanhos = item_data.get("tamanhos", [])
        if tamanhos and isinstance(tamanhos, list):
            preco = tamanhos[0].get("preco", 0)
            if preco:
                return float(preco)

        variacoes = item_data.get("variacoes", [])
        if variacoes and isinstance(variacoes, list):
            preco = variacoes[0].get("preco", 0)
            if preco:
                return float(preco)

        return float(item_data.get("preco", item_data.get("price", 0)))

    def _build_menu_text(self, items: list[MenuItem], categories: list[str]) -> str:
        lines = ["CARDÁPIO:"]
        by_category: dict[str, list[MenuItem]] = {}
        for item in items:
            by_category.setdefault(item.category, []).append(item)

        for cat in categories:
            lines.append(f"\n## {cat}")
            for item in by_category.get(cat, []):
                availability = "" if item.is_available else " (INDISPONÍVEL)"
                lines.append(
                    f"- {item.name}: R$ {item.price:.2f}"
                    f"{' - ' + item.description if item.description else ''}"
                    f"{availability}"
                )
        return "\n".join(lines)

    def _extract_address(self, data: dict) -> Optional[str]:
        """Build full address string from Tacto rag-full address fields."""
        logradouro = data.get("endLogradouro", "")
        numero = data.get("endNumero", "")
        complemento = data.get("endComplemento", "")
        bairro = data.get("endBairroNome", "")
        cidade = data.get("endCidadeNome", "")
        uf = data.get("endUFSigla", "")
        cep = data.get("endCep", "")

        if not logradouro and not cidade:
            return None

        parts = [f"{logradouro}, {numero}".strip(", ")]
        if complemento:
            parts.append(complemento)
        if bairro:
            parts.append(bairro)
        if cidade and uf:
            parts.append(f"{cidade} - {uf}")
        elif cidade:
            parts.append(cidade)
        if cep:
            parts.append(f"CEP {cep}")

        return ", ".join(p for p in parts if p)

    _PT_DAY_TO_EN: dict[str, str] = {
        "segunda": "monday",
        "terca": "tuesday",
        "terça": "tuesday",
        "quarta": "wednesday",
        "quinta": "thursday",
        "sexta": "friday",
        "sabado": "saturday",
        "sábado": "saturday",
        "domingo": "sunday",
        "seg": "monday",
        "ter": "tuesday",
        "qua": "wednesday",
        "qui": "thursday",
        "sex": "friday",
        "sab": "saturday",
        "dom": "sunday",
        "1": "monday",
        "2": "tuesday",
        "3": "wednesday",
        "4": "thursday",
        "5": "friday",
        "6": "saturday",
        "7": "sunday",
    }

    def _extract_opening_hours_dict(self, data: dict) -> dict:
        """Parse horarioAtendimentoDelivery into structured OpeningHours dict."""
        horarios = data.get("horarioAtendimentoDelivery", [])
        if not horarios:
            return {}

        result: dict[str, dict] = {}
        for h in horarios:
            dia_raw = str(h.get("diaDaSemana") or h.get("diaDaSemanaSigla") or h.get("diaSemana") or "")
            abertura = h.get("horarioAbertura", "") or ""
            fechamento = h.get("horarioFechamento", "") or ""

            if not dia_raw:
                continue

            # Normalize: lowercase, remove accents approximation, get first word
            dia_norm = dia_raw.lower().split("-")[0].strip()
            day_en = self._PT_DAY_TO_EN.get(dia_norm)
            if not day_en:
                continue

            if abertura and fechamento:
                result[day_en] = {
                    "opens_at": abertura[:5],
                    "closes_at": fechamento[:5],
                }
            else:
                result[day_en] = {"is_closed": True}

        return result

    def _extract_hours_text(self, data: dict) -> str:
        """Format horarioAtendimentoDelivery into readable text."""
        horarios = data.get("horarioAtendimentoDelivery", [])
        if not horarios:
            return ""

        lines = []
        for h in horarios:
            dia = h.get("diaDaSemana") or h.get("diaDaSemanaSigla", "")
            abertura = h.get("horarioAbertura", "")
            fechamento = h.get("horarioFechamento", "")
            if dia and abertura and fechamento:
                # Remove seconds from time strings (17:30:00 → 17:30)
                abertura = abertura[:5]
                fechamento = fechamento[:5]
                lines.append(f"- {dia}: {abertura} às {fechamento}")

        return "\n".join(lines)

    def _build_institutional_text(self, data: dict) -> str:
        lines = ["INFORMAÇÕES DO ESTABELECIMENTO:"]
        if nome := data.get("nome", data.get("name")):
            lines.append(f"Nome: {nome}")
        if endereco := data.get("endereco", data.get("address")):
            lines.append(f"Endereço: {endereco}")
        if telefone := data.get("telefone", data.get("phone")):
            lines.append(f"Telefone: {telefone}")
        payment = data.get("formas_pagamento", data.get("payment_methods", []))
        if payment:
            if isinstance(payment, list):
                payment = ", ".join(payment)
            lines.append(f"Formas de Pagamento: {payment}")
        if entrega := data.get("info_entrega", data.get("delivery_info")):
            lines.append(f"Entrega: {entrega}")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Level 2 Enhanced Methods (Order Taking)                            #
    # ------------------------------------------------------------------ #

    async def search_menu_with_prices(
        self,
        restaurant_id: RestaurantId,
        query: str,
        limit: int = 30,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[list[dict]] | Failure[Exception]:
        """
        Search menu items with full price information for Level 2 agent.

        Returns items with all variations and prices for accurate order taking.
        Uses fuzzy matching for better item recognition.

        Returns list of dicts with:
            - name: str
            - category: str
            - description: str | None
            - price: float (base price)
            - variations: list[{name, price}]
            - is_available: bool
        """
        menu_result = await self.get_menu(
            restaurant_id,
            empresa_base_id=empresa_base_id,
            grupo_empresarial=grupo_empresarial,
        )
        if isinstance(menu_result, Failure):
            return menu_result

        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        matching: list[dict] = []

        cache_key = self._cache_key("menu", restaurant_id)
        cached_raw = await self._get_cached(cache_key)

        if not cached_raw:
            return Ok([])

        cardapio = cached_raw.get("cardapio", cached_raw.get("itens", cached_raw.get("items", [])))

        for item_data in cardapio:
            if not item_data.get("disponivel", item_data.get("available", True)):
                continue

            name = (
                item_data.get("nomeCompleto")
                or item_data.get("nome")
                or item_data.get("name")
                or ""
            )
            name_lower = name.lower()

            category = item_data.get("grupo") or item_data.get("categoria") or "Outros"
            description = (
                item_data.get("textoInformativo")
                or item_data.get("descricao")
                or item_data.get("description")
            )

            score = self._calculate_match_score(query_lower, query_words, name_lower, description)

            if score > 0:
                variations = self._extract_variations(item_data)
                base_price = self._extract_price(item_data)

                matching.append({
                    "name": name,
                    "category": category,
                    "description": description,
                    "price": base_price,
                    "variations": variations,
                    "is_available": True,
                    "match_score": score,
                })

        matching.sort(key=lambda x: x["match_score"], reverse=True)

        for item in matching[:limit]:
            item.pop("match_score", None)

        return Ok(matching[:limit])

    def _calculate_match_score(
        self,
        query_lower: str,
        query_words: set[str],
        name_lower: str,
        description: Optional[str],
    ) -> float:
        """
        Calculate relevance score for fuzzy matching.

        Higher score = better match.
        """
        score = 0.0

        if query_lower == name_lower:
            return 100.0

        if query_lower in name_lower:
            score += 50.0

        name_words = set(name_lower.split())
        common_words = query_words & name_words
        if common_words:
            score += len(common_words) * 20.0

        for word in query_words:
            if len(word) >= 3:
                for name_word in name_words:
                    if word in name_word or name_word in word:
                        score += 10.0
                        break

        if description:
            desc_lower = description.lower()
            if query_lower in desc_lower:
                score += 5.0

        return score

    def _extract_variations(self, item_data: dict) -> list[dict]:
        """Extract all size/variation options with prices."""
        variations = []

        tamanhos = item_data.get("tamanhos", [])
        for tam in tamanhos:
            nome = tam.get("nome") or tam.get("tamanho") or tam.get("descricao") or ""
            preco = float(tam.get("preco", 0))
            if nome and preco > 0:
                variations.append({"name": nome, "price": preco})

        variacoes = item_data.get("variacoes", [])
        for var in variacoes:
            nome = var.get("nome") or var.get("descricao") or ""
            preco = float(var.get("preco", 0))
            if nome and preco > 0:
                variations.append({"name": nome, "price": preco})

        return variations

    async def get_item_by_name(
        self,
        restaurant_id: RestaurantId,
        item_name: str,
        variation: Optional[str] = None,
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[Optional[dict]] | Failure[Exception]:
        """
        Get exact item by name with price.

        Used by Level 2 agent to confirm items before adding to cart.

        Args:
            restaurant_id: Restaurant ID
            item_name: Exact or partial item name
            variation: Optional size/variation name

        Returns:
            Item dict with name, price, variation or None if not found
        """
        search_result = await self.search_menu_with_prices(
            restaurant_id,
            item_name,
            limit=5,
            empresa_base_id=empresa_base_id,
            grupo_empresarial=grupo_empresarial,
        )

        if isinstance(search_result, Failure):
            return search_result

        items = search_result.value
        if not items:
            return Ok(None)

        best_match = items[0]

        if variation and best_match.get("variations"):
            variation_lower = variation.lower().strip()
            for var in best_match["variations"]:
                if variation_lower in var["name"].lower():
                    return Ok({
                        "name": best_match["name"],
                        "variation": var["name"],
                        "price": var["price"],
                        "category": best_match["category"],
                        "description": best_match.get("description"),
                    })

        if best_match.get("variations"):
            first_var = best_match["variations"][0]
            return Ok({
                "name": best_match["name"],
                "variation": first_var["name"],
                "price": first_var["price"],
                "category": best_match["category"],
                "description": best_match.get("description"),
            })

        return Ok({
            "name": best_match["name"],
            "variation": None,
            "price": best_match["price"],
            "category": best_match["category"],
            "description": best_match.get("description"),
        })

    def build_rag_context_with_prices(self, items: list[dict]) -> str:
        """
        Build RAG context string with prices for Level 2 prompt.

        Args:
            items: List of menu items from search_menu_with_prices

        Returns:
            Formatted string for prompt injection
        """
        if not items:
            return "Cardápio não disponível no momento."

        by_category: dict[str, list[dict]] = {}
        for item in items:
            category = item.get("category", "Outros")
            by_category.setdefault(category, []).append(item)

        lines = []
        for category in sorted(by_category.keys()):
            lines.append(f"\n### {category}")
            for item in by_category[category]:
                name = item.get("name", "")
                description = item.get("description", "")
                variations = item.get("variations", [])

                if variations:
                    for var in variations:
                        var_name = var.get("name", "")
                        var_price = var.get("price", 0)
                        line = f"- {name} ({var_name}): R$ {var_price:.2f}"
                        if description:
                            line += f" — {description[:80]}"
                        lines.append(line)
                else:
                    price = item.get("price", 0)
                    line = f"- {name}: R$ {price:.2f}"
                    if description:
                        line += f" — {description[:80]}"
                    lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Level 2 Semantic Search with Prices (pgvector + Tacto API)         #
    # ------------------------------------------------------------------ #

    async def enrich_pgvector_results_with_prices(
        self,
        restaurant_id: RestaurantId,
        pgvector_results: list[dict],
        empresa_base_id: Optional[str] = None,
        grupo_empresarial: Optional[str] = None,
    ) -> Success[list[dict]] | Failure[Exception]:
        """
        Enrich pgvector search results with REAL prices from Tacto API.

        This method takes items found via pgvector semantic search and
        matches them with the Tacto cardápio to get ACCURATE prices.

        CRITICAL: Only returns items that exist in BOTH pgvector AND Tacto.
        This guarantees we NEVER return fake items or wrong prices.

        Args:
            restaurant_id: Restaurant ID
            pgvector_results: Results from VectorStore.search_menu()
                Each item has: content, metadata, similarity
            empresa_base_id: Tacto empresa_base_id
            grupo_empresarial: Tacto grupo_empresarial

        Returns:
            List of items with verified names and REAL prices from Tacto
        """
        if not pgvector_results:
            return Ok([])

        # Get full menu from Tacto (cached in Redis)
        menu_result = await self.get_menu(
            restaurant_id,
            empresa_base_id=empresa_base_id,
            grupo_empresarial=grupo_empresarial,
        )
        if isinstance(menu_result, Failure):
            return menu_result

        # Get raw cardápio for price extraction
        cache_key = self._cache_key("menu", restaurant_id)
        cached_raw = await self._get_cached(cache_key)
        if not cached_raw:
            logger.warning("enrich_prices_no_cache", restaurant_id=str(restaurant_id.value))
            return Ok([])

        cardapio = cached_raw.get("cardapio", cached_raw.get("itens", cached_raw.get("items", [])))

        # Build lookup dict: normalized name -> full item data
        tacto_items: dict[str, dict] = {}
        for item_data in cardapio:
            if not item_data.get("disponivel", item_data.get("available", True)):
                continue

            name = (
                item_data.get("nomeCompleto")
                or item_data.get("nome")
                or item_data.get("name")
                or ""
            )
            if name:
                tacto_items[name.lower().strip()] = item_data

        # Match pgvector results with Tacto items
        enriched: list[dict] = []
        for pv_item in pgvector_results:
            metadata = pv_item.get("metadata", {})
            pv_name = metadata.get("name", "")
            pv_name_lower = pv_name.lower().strip()

            # Try exact match first
            tacto_item = tacto_items.get(pv_name_lower)

            # Try partial match if exact fails
            if not tacto_item:
                for tacto_name, tacto_data in tacto_items.items():
                    if pv_name_lower in tacto_name or tacto_name in pv_name_lower:
                        tacto_item = tacto_data
                        break

            if not tacto_item:
                # Item not found in Tacto — SKIP (never invent)
                logger.debug(
                    "pgvector_item_not_in_tacto_skipping",
                    item_name=pv_name,
                    restaurant_id=str(restaurant_id.value),
                )
                continue

            # Extract REAL data from Tacto
            real_name = (
                tacto_item.get("nomeCompleto")
                or tacto_item.get("nome")
                or tacto_item.get("name")
                or pv_name
            )
            category = tacto_item.get("grupo") or tacto_item.get("categoria") or "Outros"
            description = (
                tacto_item.get("textoInformativo")
                or tacto_item.get("descricao")
                or tacto_item.get("description")
            )
            variations = self._extract_variations(tacto_item)
            base_price = self._extract_price(tacto_item)

            enriched.append({
                "name": real_name,
                "category": category,
                "description": description,
                "price": base_price,
                "variations": variations,
                "is_available": True,
                "similarity": pv_item.get("similarity", 0),
            })

        # Sort by semantic similarity
        enriched.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        logger.info(
            "pgvector_enriched_with_prices",
            restaurant_id=str(restaurant_id.value),
            pgvector_count=len(pgvector_results),
            enriched_count=len(enriched),
        )

        return Ok(enriched)
