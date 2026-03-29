"""
Level 1 (BASIC) AI Prompts.

Humanized prompts for informational responses.
Focus on natural conversation, menu URL sharing, and customer engagement.
Pure domain logic — no I/O, no framework dependencies.
"""

import random
from typing import Any, Optional


class Level1Prompts:
    """Prompt templates for Level 1 (BASIC) automation."""

    SYSTEM_PROMPT = """Você é {attendant_name}, atendente do {restaurant_name}.

## QUEM VOCÊ É
Você é uma atendente humana — nunca diga que é IA, robô, assistente virtual ou chatbot. Se perguntarem diretamente, desvie com naturalidade: "Sou a {attendant_name}, atendente daqui 😄". Você conhece o cardápio de cor, tem opinião própria sobre os pratos e adora ajudar o cliente a encontrar algo que vai amar.

## SEU PAPEL (NÍVEL 1 — ATENDENTE INFORMATIVA)
Você é uma atendente informativa. Não tem acesso a preços — eles ficam no cardápio online.

**Dois modos de resposta:**

MODO INFORMATIVO — use quando o cliente perguntar sobre ingredientes, pedir sugestão, querer saber o que tem no prato:
→ Use os ITENS RELEVANTES abaixo para descrever, sugerir e recomendar com fluidez.
→ Responda de forma natural, como uma atendente que conhece cada item de cor.

MODO CARDÁPIO — use quando o cliente quiser ver preços, fazer pedido, delivery, ou pedir o link do cardápio:
→ Responda em UMA frase curta e direta. Exemplo: "Aqui está o cardápio 😊" ou "Pode fazer o pedido pelo link:"
→ O link do cardápio será incluído automaticamente após sua resposta — não invente nem repita o link.
→ Nunca liste itens nem descreva ingredientes nesse modo.

## COMO VOCÊ FALA
- Curto e direto. Máximo 2 frases por resposta — exceto ao listar ingredientes.
- Tom de conversa real: como uma atendente simpática que está ali do lado.
- Use "a gente", "aqui", "temos" — fale como parte do restaurante.
- **Nunca** comece com "Claro!", "Com certeza!", "Ótima escolha!", "Perfeito!" ou qualquer frase de chatbot.
- Use o nome do cliente só na primeira mensagem da conversa. Depois, fale naturalmente sem nome.
- Emoji: zero ou um por mensagem, só quando cair bem. Nunca enfileirar.
- Nunca termine com "Posso te ajudar com mais alguma coisa?" — isso soa robótico.
- Nunca use listas com bullets/números para respostas simples. Só em ingredientes ou opções múltiplas.

## PRIMEIRA MENSAGEM DA CONVERSA
Se for a primeira mensagem do cliente (memória vazia), cumprimente de forma curta e espere ele continuar — não faça perguntas abertas. Se ele já mandou o que precisa, responda direto sem cumprimento separado.
- ✅ "Oi! Pode falar o que precisar."
- ✅ (cliente perguntou algo) → responda direto, com "Oi!" só se natural na frase.
- ❌ "Olá! Seja bem-vindo(a) ao restaurante! Como posso te ajudar hoje?"

## INGREDIENTES (MODO INFORMATIVO)
Quando listar ingredientes, use apenas os da seção "ITENS RELEVANTES" abaixo. Nunca invente. Pode apresentar de forma fluída, mas sem omitir itens listados. Se um ingrediente não constar nos itens listados, não mencione.

## COMO SUGERIR ITENS (RACIOCÍNIO SEMÂNTICO)
Quando o cliente pedir sugestão, raciocine pelos ingredientes e perfil do item, não pelo nome.
- "Pizza exótica" → combinações incomuns: frutas, queijos fortes, defumados, pimentas
- "Algo leve" → vegetais, molhos suaves, sem massa pesada
- "Algo especial" → ingredientes premium ou combinações únicas
- "Sabor marcante" → defumados, pimentas, queijos curados
Use os ingredientes do cardápio para justificar a sugestão com 1 frase sedutora. Nunca mencione preço.

## REGRAS ABSOLUTAS
1. **JAMAIS** mencione preço, valor ou qualquer dado financeiro — os itens abaixo já vêm sem preço.
2. Use SOMENTE o link exato da seção "CARDÁPIO" abaixo. Nunca invente, encurte ou troque.
3. Quando for enviar o link, seja breve — o link é incluído automaticamente. Não repita nem invente.
4. Informe endereço e horário apenas quando perguntado.

## CARDÁPIO (link para preços e pedido)
{menu_url}

## ITENS RELEVANTES PARA ESTA CONVERSA
{rag_context}

## ENDEREÇO
{tacto_address}

## HORÁRIO DE FUNCIONAMENTO
{opening_hours}

## INSTRUÇÕES DO RESTAURANTE
{custom_prompt}

---

## CONTEXTO DO CLIENTE
{memory_context}"""

    # ---------------------------------------------------------------------------
    # Keyword lists
    # ---------------------------------------------------------------------------

    # Triggers envio do link do cardápio — apenas quando preço/pedido é solicitado.
    # Itens de comida genéricos (pizza, hamburguer, etc.) NÃO estão aqui:
    # eles devem acionar o RAG semântico, não mandar link direto.
    MENU_TRIGGER_KEYWORDS = [
        # Ver cardápio / menu
        "cardápio",
        "cardapio",
        "menu",
        "ver o cardápio",
        "ver o cardapio",
        "ver cardápio",
        "ver cardapio",
        "acessar o cardápio",
        "acessar o cardapio",
        "link do cardápio",
        "link do cardapio",
        "link do menu",
        "manda o cardápio",
        "manda o cardapio",
        "me manda o cardápio",
        "me manda o cardapio",
        # Preço / valor
        "preço",
        "preco",
        "preços",
        "precos",
        "quanto custa",
        "quanto é",
        "quanto e",
        "qual o valor",
        "qual valor",
        "valor",
        "valores",
        "tabela de preços",
        "tabela de precos",
        # Intenção de pedido / compra
        "fazer pedido",
        "fazer o pedido",
        "quero fazer",
        "quero pedir",
        "como peço",
        "como faço pedido",
        "como faço um pedido",
        "pedir pelo",
        "pedido online",
        "quero comprar",
        "fazer um pedido",
        # Delivery / entrega
        "delivery",
        "entrega",
        "faz entrega",
        "tem delivery",
        "motoboy",
        "pedir entrega",
        "pedido para entrega",
        "quero delivery",
        # Retirada
        "retirada",
        "retirar",
        "buscar no local",
        "pegar no local",
    ]

    HUMAN_HANDOFF_KEYWORDS = [
        "falar com atendente",
        "falar com um atendente",
        "atendimento humano",
        "falar com pessoa",
        "falar com humano",
        "quero falar com alguém",
        "quero falar com alguem",
        "chamar atendente",
        "atendente humano",
        "falar com responsável",
        "falar com responsavel",
        "suporte humano",
        "atendimento real",
        "falar com funcionário",
        "falar com funcionario",
        "preciso de ajuda humana",
        "quero atendimento humano",
        "quero um atendente",
        "preciso de um atendente",
        "me transfere",
        "me transfere para",
        "transferir para atendente",
        "falar com gerente",
        "chamar gerente",
        "quero falar com alguém de verdade",
        "quero falar com uma pessoa",
    ]

    # ---------------------------------------------------------------------------
    # Menu URL templates — formatados para WhatsApp (texto nativo)
    # ---------------------------------------------------------------------------

    # Templates para quando o cliente pede o cardápio / preços / delivery
    # Formatação WhatsApp: *negrito*, _itálico_, emojis, quebras de linha
    # O {url} é injetado pelo código — a IA nunca manipula o link diretamente.
    _MENU_URL_TEMPLATES = [
        "*📋 Cardápio {restaurant_name}*\n\nVeja os preços e faça seu pedido pelo link:\n{url}\n\n_Qualquer dúvida sobre algum item, é só chamar!_",
        "*🛒 Cardápio e pedidos*\n\n{url}\n\n_Pelo link você vê tudo, com preços e opções de entrega!_",
        "Aqui o cardápio completo 👇\n\n*{url}*\n\n_É por lá que fica o preço e você faz o pedido._",
        "*📋 {restaurant_name}*\n\nCardápio com preços e pedido online:\n{url}",
    ]

    # Templates específicos para quando o cliente pergunta sobre delivery/entrega
    _DELIVERY_URL_TEMPLATES = [
        "*🛵 Delivery disponível!*\n\nFaça seu pedido pelo cardápio:\n{url}\n\n_Veja os preços, monte seu pedido e escolha entrega ou retirada._",
        "*🍕 Pedido online*\n\nAcesse o cardápio e escolha a entrega:\n{url}",
        "A gente faz entrega sim! 🛵\n\nFaça o pedido pelo link:\n{url}",
    ]

    # ---------------------------------------------------------------------------
    # Response variations for fixed responses (random.choice keeps naturalidade)
    # ---------------------------------------------------------------------------

    _CLOSED_RESPONSES = [
        "A gente tá fechado agora. {next_opening}.\nMas já dá pra dar uma olhada no cardápio e escolher com calma:\n👉 {menu_url}",
        "Fechados no momento! {next_opening}.\nEnquanto isso, o cardápio tá disponível:\n👉 {menu_url}",
        "Ainda não abrimos. {next_opening}.\nSe quiser, já dá pra conferir o cardápio:\n👉 {menu_url}",
        "Opa, a gente só abre {next_opening}. Mas pode já escolher pelo cardápio:\n👉 {menu_url}",
    ]

    _HANDOFF_RESPONSES = [
        "Tá bom, deixa eu chamar alguém aqui pra te ajudar. Aguarda um momento! 😊",
        "Certo! Vou acionar um atendente do {restaurant} agora. Um instante.",
        "Sem problema! Um momento que a gente chama alguém pra te ajudar pessoalmente. 🙏",
        "Fica tranquilo, já chamo alguém do {restaurant} pra falar contigo.",
    ]

    # Legado — mantido para compatibilidade; prefer get_human_handoff_response()
    HUMAN_HANDOFF_RESPONSE = "Tá bom, deixa eu chamar alguém aqui pra te ajudar. Aguarda um momento! 😊"

    # Legado — mantido para compatibilidade; prefer get_closed_response()
    CLOSING_HOURS_RESPONSE = (
        "A gente tá fechado agora. {next_opening}.\n"
        "Mas já dá pra conferir o cardápio:\n👉 {menu_url}"
    )

    # ---------------------------------------------------------------------------
    # Public class methods
    # ---------------------------------------------------------------------------

    @classmethod
    def build_system_prompt(
        cls,
        restaurant_name: str,
        menu_url: str,
        opening_hours: dict[str, Any],
        custom_prompt: str,
        customer_name: Optional[str] = None,
        short_term_memory: str = "",
        medium_term_memory: str = "",
        long_term_memory: str = "",
        rag_context: str = "",
        tacto_address: str = "",
        tacto_hours: str = "",
        attendant_name: str = "Maria",
    ) -> str:
        """Build the complete system prompt with three-level memory context."""
        hours_text = tacto_hours.strip() if tacto_hours else cls._format_opening_hours(opening_hours)
        address_text = tacto_address.strip() if tacto_address else "Endereço não disponível."

        menu_url_text = (
            menu_url.strip()
            if menu_url and menu_url.strip()
            else "Cardápio temporariamente indisponível. Não forneça links externos."
        )

        rag_text = (
            rag_context.strip()
            if rag_context
            else "Sem itens específicos para esta conversa. Indique o cardápio se o cliente perguntar sobre algum item."
        )

        custom_text = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else ""

        memory_context = cls._build_memory_context(
            customer_name=customer_name,
            short_term=short_term_memory,
            medium_term=medium_term_memory,
            long_term=long_term_memory,
        )

        return cls.SYSTEM_PROMPT.format(
            attendant_name=attendant_name,
            restaurant_name=restaurant_name,
            menu_url=menu_url_text,
            opening_hours=hours_text,
            tacto_address=address_text,
            custom_prompt=custom_text,
            rag_context=rag_text,
            memory_context=memory_context,
        )

    @classmethod
    def should_send_menu(cls, message: str) -> bool:
        """Check if message should trigger menu URL response."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in cls.MENU_TRIGGER_KEYWORDS)

    @classmethod
    def is_delivery_request(cls, message: str) -> bool:
        """Check if the message is specifically about delivery/entrega."""
        delivery_kws = {"delivery", "entrega", "faz entrega", "tem delivery", "motoboy",
                        "pedir entrega", "quero delivery"}
        message_lower = message.lower()
        return any(kw in message_lower for kw in delivery_kws)

    @classmethod
    def is_human_handoff_request(cls, message: str) -> bool:
        """Check if message is requesting a human agent."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in cls.HUMAN_HANDOFF_KEYWORDS)

    @classmethod
    def format_menu_url_block(
        cls,
        url: str,
        restaurant_name: str,
        message: str = "",
    ) -> str:
        """
        Return a WhatsApp-formatted block containing the menu URL.

        Uses native WhatsApp text formatting (*bold*, _italic_, emojis).
        Chooses the delivery-specific template when the original message
        was about delivery/entrega; otherwise picks from general templates.

        Args:
            url: The restaurant's menu URL (already validated).
            restaurant_name: Restaurant name for personalization.
            message: Original customer message (used to choose template).

        Returns:
            Formatted string ready to append to the agent response.
        """
        if message and cls.is_delivery_request(message):
            template = random.choice(cls._DELIVERY_URL_TEMPLATES)
        else:
            template = random.choice(cls._MENU_URL_TEMPLATES)
        return template.format(url=url, restaurant_name=restaurant_name)

    @classmethod
    def get_human_handoff_response(cls, customer_name: str, restaurant_name: str) -> str:
        """Get a natural, varied human handoff response."""
        return random.choice(cls._HANDOFF_RESPONSES).format(restaurant=restaurant_name)

    @classmethod
    def get_closed_response(cls, menu_url: str, next_opening: str) -> str:
        """Get a natural, varied closed-restaurant response."""
        return random.choice(cls._CLOSED_RESPONSES).format(
            next_opening=next_opening,
            menu_url=menu_url,
        )

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    @classmethod
    def _build_memory_context(
        cls,
        customer_name: Optional[str],
        short_term: str,
        medium_term: str,
        long_term: str,
    ) -> str:
        """
        Build the memory context block injected into the system prompt.

        Only includes sections that have actual content, avoiding robotic
        placeholder text. The LLM sees a clean, natural context.

        Examples of natural memory usage the LLM should follow:
        - long_term: "Cliente gosta de pizzas com bordas recheadas e prefere sabores
          tradicionais. Na última visita pediu Calabresa com Cheddar."
          → Ao sugerir, mencione: "Você costuma gostar de borda recheada, né?
            A gente tem uma Calabresa nova que acho que vai curtir."
        - medium_term: "Pediu frango com catupiry há 3 dias."
          → "Da última vez você veio de Frango com Catupiry — quer repetir
            ou experimentar algo diferente?"
        - short_term: conversa atual já carregada no histórico — não precisa repetir aqui.
        """
        parts: list[str] = []

        # Nome do cliente — injetado apenas se disponível
        if customer_name:
            parts.append(f"Nome do cliente: {customer_name}")

        # Longo prazo: preferências e histórico consolidado
        if long_term.strip():
            parts.append(f"Histórico e preferências:\n{long_term.strip()}")

        # Médio prazo: visitas e pedidos recentes
        if medium_term.strip():
            parts.append(f"Visitas recentes:\n{medium_term.strip()}")

        # Curto prazo: contexto da conversa atual
        if short_term.strip():
            parts.append(f"Conversa atual:\n{short_term.strip()}")

        if not parts:
            return "Primeira conversa — sem histórico. Trate como novo cliente."

        usage_hint = (
            "\nUse o contexto acima para personalizar a resposta. "
            "Mencione histórico de forma natural, como uma atendente que lembra do cliente — "
            "nunca como se estivesse lendo uma ficha."
        )

        return "\n\n".join(parts) + usage_hint

    @classmethod
    def _format_opening_hours(cls, hours: dict[str, Any]) -> str:
        """Format opening hours dict for display in the system prompt."""
        if not hours:
            return "Horário não informado."

        days_pt = {
            "monday": "Segunda",
            "tuesday": "Terça",
            "wednesday": "Quarta",
            "thursday": "Quinta",
            "friday": "Sexta",
            "saturday": "Sábado",
            "sunday": "Domingo",
        }

        lines = []
        for day, info in hours.items():
            day_name = days_pt.get(day.lower(), day)
            if isinstance(info, dict):
                if info.get("closed"):
                    lines.append(f"- {day_name}: Fechado")
                else:
                    open_time = info.get("open", "")
                    close_time = info.get("close", "")
                    lines.append(f"- {day_name}: {open_time} às {close_time}")
            elif isinstance(info, str):
                lines.append(f"- {day_name}: {info}")

        return "\n".join(lines) if lines else "Horário não informado."
