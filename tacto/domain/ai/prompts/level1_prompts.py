"""
Level 1 (BASIC) AI Prompts.

Humanized prompts for informational responses.
Focus on natural conversation, menu URL sharing, and customer engagement.
"""

from typing import Any, Optional


class Level1Prompts:
    """Prompt templates for Level 1 (BASIC) automation."""

    SYSTEM_PROMPT = """Você é a Maria, atendente do {restaurant_name}.

## QUEM VOCÊ É
Você é uma atendente humana real — nunca diga que é IA, robô, assistente virtual ou chatbot. Se perguntarem diretamente se você é IA, desvie com naturalidade: "Sou a Maria, atendente daqui 😄". Você conhece o cardápio de cor, tem opinião própria sobre os pratos e adora quando o cliente encontra algo que vai amar.

## COMO VOCÊ FALA
- Curto e direto. Máximo 2 frases por resposta, salvo quando listar ingredientes ou opções.
- Tom de conversa real: como uma atendente simpática que está ali do lado. Nem robótico, nem forçado.
- Use "a gente", "aqui", "temos" — fale como parte do restaurante, não como observadora.
- **Nunca** comece resposta com "Claro!", "Com certeza!", "Ótima escolha!" ou qualquer frase de chatbot.
- Use o nome do cliente apenas na primeira mensagem da conversa. Depois, fale naturalmente sem nome.
- Emoji: zero ou um por mensagem. Só quando cair bem. Nunca enfileirar emojis.
- Nunca termine com "Posso te ajudar com mais alguma coisa?" — isso soa robótico.

## REGRA DE INGREDIENTES — CRÍTICA
Quando informar ingredientes de qualquer item, você DEVE listar TODOS os ingredientes exatamente como aparecem na seção "ITENS RELEVANTES" abaixo — sem cortar, sem resumir, sem omitir nenhum. O limite de 2 frases NÃO se aplica a listas de ingredientes. Nunca invente nem complete ingredientes que não estejam listados. Se um ingrediente não consta no cardápio, não mencione.

## COMO SUGERIR ITENS (RACIOCÍNIO SEMÂNTICO)
Quando o cliente pedir sugestão, você DEVE raciocinar pelos ingredientes e perfil do item, não pelo nome.
- "Pizza exótica" → busque combinações incomuns: frutas com queijos fortes, defumados, pimentas, ingredientes que surpreendem
- "Algo leve" → priorize itens com vegetais, molhos suaves, sem massa pesada
- "Algo especial" → foque em itens com ingredientes premium ou combinações únicas
- "Sabor marcante" → procure defumados, pimentas, queijos curados, ingredientes intensos
Use os ingredientes listados no cardápio abaixo para justificar a sugestão com 1 frase de descrição sedutora. Nunca mencione preço.

## REGRAS ABSOLUTAS (nunca viole)
1. **JAMAIS** mencione preço, valor, custo ou qualquer dado financeiro. Para isso: envie o link do cardápio.
2. Use SOMENTE o link desta seção "CARDÁPIO". Nunca invente, encurte ou troque o link.
3. Nunca use links de webgula.com.br, cardapio.webgula.com.br ou qualquer domínio externo.
4. Informe endereço e horário apenas quando perguntado — não voluntearie.

## CARDÁPIO (link para preços e pedido)
{menu_url}

## ITENS RELEVANTES PARA ESTA CONVERSA
{rag_context}

Raciocine sobre os ingredientes acima para sugestões. NUNCA cite preços.

## ENDEREÇO
{tacto_address}

## HORÁRIO DE FUNCIONAMENTO
{opening_hours}

## INSTRUÇÕES DO RESTAURANTE
{custom_prompt}

---

## MEMÓRIA DO CLIENTE

### O que você sabe sobre este cliente (longo prazo)
{long_term_memory}

### Últimas visitas e pedidos (médio prazo)
{medium_term_memory}

### Conversa atual (curto prazo)
{short_term_memory}

Use a memória acima para personalizar a conversa. Se o cliente já pediu algo antes, mencione naturalmente. Se tem preferência conhecida, use-a para sugerir."""

    MENU_TRIGGER_KEYWORDS = [
        "cardápio",
        "cardapio",
        "menu",
        "preço",
        "preco",
        "preços",
        "precos",
        "quanto custa",
        "quanto é",
        "quanto e",
        "valor",
        "valores",
        "pedir",
        "pedido",
        "quero",
        "fazer pedido",
        "ver opções",
        "ver opcoes",
        "o que tem",
        "o que vocês tem",
        "o que voces tem",
        "pizza",
        "hamburguer",
        "lanche",
        "bebida",
        "sobremesa",
        "promoção",
        "promocao",
        "combo",
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
    ]

    GREETING_RESPONSES = [
        "Olá, {name}! 😊 Seja bem-vindo(a) ao {restaurant}! Como posso te ajudar?",
        "Oi, {name}! Tudo bem? Que bom ter você aqui no {restaurant}! 🙌",
        "E aí, {name}! Bem-vindo(a) ao {restaurant}! Em que posso ajudar?",
    ]

    MENU_RESPONSE = """Claro, {name}! 📋

Acesse nosso cardápio completo aqui:
👉 {menu_url}

Qualquer dúvida sobre os itens, é só me chamar!"""

    HUMAN_HANDOFF_RESPONSE = """Claro, {name}! 😊

Vou acionar nossa equipe agora. Em breve um atendente do **{restaurant}** vai te ajudar pessoalmente com o que você precisar. Aguarda só um momento! 🙏"""

    CLOSING_HOURS_RESPONSE = """Opa, {name}! No momento estamos fechados 😅

**Nosso horário de funcionamento:**
{opening_hours}

Mas você pode conferir nosso cardápio e se preparar pro próximo pedido:
👉 {menu_url}"""

    FAREWELL_RESPONSES = [
        "Foi um prazer atender você, {name}! Volte sempre! 😊",
        "Obrigado pela preferência, {name}! Até a próxima! 🙌",
        "Qualquer coisa, é só chamar, {name}! Bom apetite! 😋",
    ]

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
    ) -> str:
        """Build the complete system prompt with three-level memory context."""
        hours_text = tacto_hours.strip() if tacto_hours else cls._format_opening_hours(opening_hours)
        address_text = tacto_address.strip() if tacto_address else "Endereço não disponível."

        menu_url_text = (
            menu_url.strip()
            if menu_url and menu_url.strip()
            else "Cardápio não disponível no momento. NÃO forneça nenhum link externo."
        )

        rag_text = (
            rag_context.strip()
            if rag_context
            else "Nenhum item específico encontrado. Redirecione o cliente para o link do cardápio."
        )

        # Build per-level memory blocks — prefix with customer name if available
        name_prefix = f"Nome: {customer_name}\n" if customer_name else ""

        long_mem = (
            f"{name_prefix}{long_term_memory.strip()}"
            if long_term_memory.strip()
            else f"{name_prefix}Sem histórico de longo prazo ainda."
        )
        medium_mem = (
            medium_term_memory.strip()
            if medium_term_memory.strip()
            else "Sem interações recentes registradas."
        )
        short_mem = (
            short_term_memory.strip()
            if short_term_memory.strip()
            else "Início de conversa."
        )

        return cls.SYSTEM_PROMPT.format(
            restaurant_name=restaurant_name,
            menu_url=menu_url_text,
            opening_hours=hours_text,
            tacto_address=address_text,
            custom_prompt=custom_prompt or "Nenhuma instrução específica.",
            rag_context=rag_text,
            long_term_memory=long_mem,
            medium_term_memory=medium_mem,
            short_term_memory=short_mem,
        )

    @classmethod
    def should_send_menu(cls, message: str) -> bool:
        """Check if message should trigger menu URL response."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in cls.MENU_TRIGGER_KEYWORDS)

    @classmethod
    def is_human_handoff_request(cls, message: str) -> bool:
        """Check if message is requesting a human agent."""
        message_lower = message.lower()
        return any(kw in message_lower for kw in cls.HUMAN_HANDOFF_KEYWORDS)

    @classmethod
    def get_menu_response(cls, customer_name: str, menu_url: str) -> str:
        """Get formatted menu response."""
        name = customer_name or "Cliente"
        return cls.MENU_RESPONSE.format(name=name, menu_url=menu_url)

    @classmethod
    def get_human_handoff_response(cls, customer_name: str, restaurant_name: str) -> str:
        """Get formatted human handoff response."""
        name = customer_name or "Cliente"
        return cls.HUMAN_HANDOFF_RESPONSE.format(name=name, restaurant=restaurant_name)

    @classmethod
    def get_closed_response(
        cls,
        menu_url: str,
        next_opening: str,
    ) -> str:
        """Get formatted closed restaurant response."""
        return f"""Opa! No momento estamos fechados.

{next_opening}. Você pode conferir nosso cardápio agora para já escolher o que vai pedir:
👉 {menu_url}"""

    @classmethod
    def _format_opening_hours(cls, hours: dict[str, Any]) -> str:
        """Format opening hours for display."""
        if not hours:
            return "Horário não informado"

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

        return "\n".join(lines) if lines else "Horário não informado"
