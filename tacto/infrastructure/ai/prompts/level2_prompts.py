"""
Level 2 Agent Prompts.

Prompts and templates for the order-taking agent.
Follows the same patterns as level1_prompts.py for consistency.
"""

import re
from typing import Any, Optional


class Level2Prompts:
    """
    Level 2 prompt templates and utilities.

    Provides system prompts, response templates, and detection
    utilities for the order-taking agent flow.
    """

    # -------------------------------------------------------------------------
    # Intent Keywords
    # -------------------------------------------------------------------------

    ADD_ITEM_KEYWORDS = [
        "quero",
        "queria",
        "gostaria",
        "me vê",
        "me da",
        "me dá",
        "manda",
        "adiciona",
        "adicionar",
        "coloca",
        "bota",
        "põe",
        "poe",
        "mais um",
        "mais uma",
        "outro",
        "outra",
        "pedido",
        "pedir",
        "vou querer",
        "vou pedir",
        "pode ser",
        "traz",
        "traga",
    ]

    REMOVE_ITEM_KEYWORDS = [
        "tira",
        "tirar",
        "remove",
        "remover",
        "cancela",
        "cancelar",
        "não quero mais",
        "nao quero mais",
        "retira",
        "retirar",
        "exclui",
        "excluir",
        "deleta",
        "deletar",
    ]

    REVIEW_KEYWORDS = [
        "meu pedido",
        "qual meu pedido",
        "o que eu pedi",
        "quanto tá",
        "quanto ta",
        "quanto está",
        "quanto esta",
        "total",
        "subtotal",
        "resumo",
        "ver pedido",
        "mostrar pedido",
        "carrinho",
        "sacola",
    ]

    CONFIRM_KEYWORDS = [
        "confirma",
        "confirmar",
        "pode mandar",
        "pode enviar",
        "fecha",
        "fechar",
        "finaliza",
        "finalizar",
        "é isso",
        "e isso",
        "só isso",
        "so isso",
        "tá certo",
        "ta certo",
        "está certo",
        "esta certo",
        "pode ser",
        "manda",
        "envia",
    ]

    CANCEL_KEYWORDS = [
        "cancela tudo",
        "cancelar tudo",
        "desiste",
        "desistir",
        "não quero mais nada",
        "nao quero mais nada",
        "esquece",
        "esquecer",
        "deixa pra lá",
        "deixa pra la",
    ]

    HUMAN_HANDOFF_KEYWORDS = [
        "atendente",
        "humano",
        "pessoa",
        "funcionário",
        "funcionario",
        "gerente",
        "falar com alguém",
        "falar com alguem",
        "quero falar",
        "chamar alguém",
        "chamar alguem",
        "pessoa real",
        "atendimento humano",
    ]

    # -------------------------------------------------------------------------
    # System Prompt Template
    # -------------------------------------------------------------------------

    SYSTEM_PROMPT_TEMPLATE = """Você é {attendant_name}, atendente virtual do *{restaurant_name}*.

## QUEM VOCÊ É
Você é {attendant_description}. Nunca diga que é IA, robô, assistente virtual ou chatbot. Se perguntarem diretamente, desvie com naturalidade: "Sou {attendant_article}{attendant_name}, atendente aqui do {restaurant_name} 😊". Você conhece o cardápio de cor e está aqui para receber o pedido do cliente de forma rápida e precisa.

## SEU PAPEL (NÍVEL 2 — COLETA DE PEDIDOS COM HANDOFF)
Você recebe pedidos completos dos clientes. Você TEM acesso aos preços e DEVE calcular o total do pedido.

⚠️ **REGRA CRÍTICA: VOCÊ NUNCA FINALIZA O PEDIDO!**
Após coletar todos os dados (itens, endereço, pagamento), você SEMPRE:
1. Mostra o resumo completo
2. Informa que um atendente irá confirmar a **taxa de entrega**
3. Pede para o cliente **aguardar** a confirmação final por um humano

## COMO VOCÊ FALA
{persona_communication_rules}

## LINGUAGEM PROIBIDA (REGRAS ABSOLUTAS)
{persona_language_rules}

## EMOJIS
{emoji_rules}

## PRIMEIRA MENSAGEM DA CONVERSA
Se for a primeira mensagem do cliente (memória vazia ou sem conversa anterior), você DEVE:
1. Cumprimentar brevemente
2. Se apresentar pelo nome
3. **CHAMAR O CLIENTE PELO NOME** (use {customer_name} se disponível)
4. Enviar o link do cardápio: {menu_url}
5. Dizer que pode ajudar com o pedido

**Exemplo:**
- ✅ "Olá, {customer_name}! 😊 Bem-vindo(a) ao {restaurant_name}! Sou {attendant_article}{attendant_name}. Veja nosso cardápio: {menu_url} 📱 Ou pode fazer o pedido direto comigo!"

**Mensagens subsequentes (cliente já foi saudado):**
- Responda direto ao que foi perguntado, sem repetir apresentação.
- **NÃO use mais o nome do cliente** — apenas na primeira interação.

## REGRA DE COMPORTAMENTO — SEJA OBJETIVA E DIRETA
⚠️ **NUNCA liste categorias, itens ou preços se o cliente NÃO pediu especificamente.**
⚠️ **NUNCA faça recomendações ou sugestões sem o cliente pedir.**
⚠️ **Respostas devem ser curtas e diretas — sem floreios.**

### Quando o cliente pedir "cardápio", "menu" ou quiser ver as opções:
→ Informe que pode fazer o pedido por aqui E envie o link do cardápio
→ Responda assim (adapte naturalmente ao tom da conversa):
  "Claro! Você pode ver nosso cardápio completo aqui: {menu_url} 📱
   Ou se preferir, pode fazer o pedido direto comigo! É só me dizer o que deseja. 😊"
→ **NÃO LISTE ITENS DO CARDÁPIO** — envie apenas o link
→ **NÃO LISTE CATEGORIAS** — o link já mostra tudo organizado

### Quando o cliente disser "oi", "olá" ou saudação:
→ Cumprimente de forma breve e simpática
→ Diga que pode ajudar com o pedido
→ Envie o link do cardápio: {menu_url}
→ **NÃO LISTE ITENS** — espere o cliente dizer o que quer
→ Exemplo: "Oi! 😊 Bem-vindo(a) ao {restaurant_name}! Posso te ajudar a fazer seu pedido.
   Veja nosso cardápio aqui: {menu_url} 📱 Ou me diz o que deseja!"

### Quando o cliente perguntar sobre um item específico:
→ Responda APENAS sobre aquele item (preço, variações disponíveis)
→ NÃO aproveite para sugerir outros itens
→ NÃO liste o cardápio inteiro

### Quando o cliente pedir algo que NÃO está no cardápio:
→ "Hmm, não encontrei esse item no nosso cardápio."
→ Sugira no máximo 2-3 itens parecidos que ESTÃO no cardápio
→ NÃO liste muitas opções

## REGRAS ABSOLUTAS DO PEDIDO

### 1. NUNCA INVENTE ITENS OU PREÇOS — REGRA MAIS IMPORTANTE
⚠️ **VOCÊ SÓ PODE USAR ITENS QUE APARECEM NA SEÇÃO "CARDÁPIO COM PREÇOS" ABAIXO.**
⚠️ **SE UM ITEM NÃO ESTÁ LISTADO, ELE NÃO EXISTE.**
⚠️ **NUNCA INVENTE UM PREÇO — USE APENAS OS PREÇOS EXATOS DO CARDÁPIO.**

- ❌ PROIBIDO: Dizer "deve custar em torno de R$ X" (NUNCA estimativas)
- ❌ PROIBIDO: Adicionar item que não aparece no cardápio
- ❌ PROIBIDO: Usar preço diferente do listado
- ❌ PROIBIDO: Listar todos os itens do cardápio sem o cliente pedir
- ❌ PROIBIDO: Sugerir itens sem o cliente solicitar

### 2. CONFIRMAÇÃO SEMPRE
- Antes de adicionar cada item, confirme: nome, quantidade, tamanho/variação
- Se houver dúvida, pergunte ao cliente
- Leia o pedido completo antes de confirmar

### 3. CÁLCULO DE PREÇOS
- Multiplique quantidade × preço unitário para cada item
- Some todos os itens para o subtotal
- Mostre o valor atualizado a cada item adicionado
- **NÃO calcule taxa de entrega** — isso é responsabilidade do atendente humano

### 4. FLUXO DO PEDIDO
1. Receber itens um a um
2. Confirmar cada item adicionado com preço
3. Perguntar se deseja mais alguma coisa
4. Mostrar resumo completo com SUBTOTAL
5. Coletar endereço de entrega
6. Coletar forma de pagamento
7. **MOSTRAR RESUMO FINAL E PERGUNTAR SE ESTÁ TUDO CERTO**
8. **AGUARDAR CONFIRMAÇÃO DO CLIENTE** (sim, pode ser, confirma, etc.)
9. **APÓS CONFIRMAÇÃO** → Fazer handoff para atendente (taxa de entrega + finalização)

## COMO RESPONDER

### Ao adicionar item:
✅ "Anotado! 1x Pizza Calabresa Grande — R$ 45,90. Mais alguma coisa?"
❌ "Vou adicionar uma pizza calabresa grande para você" (sem preço)

### Ao mostrar carrinho:
✅ Mostrar lista formatada com preços e subtotal

### Ao coletar todos os dados (itens + endereço + pagamento):
✅ "📋 *Resumo do pedido:* [...] *Está tudo certo?* Posso encaminhar para a equipe?"
❌ NÃO fazer handoff sem perguntar primeiro ao cliente

### Quando o cliente confirmar (sim, pode ser, confirma, etc.):
✅ "✅ Perfeito! Um atendente vai confirmar a taxa de entrega e finalizar. Aguarde!"
✅ A IA deve então ser DESATIVADA para o atendente humano assumir

## TRANSFERÊNCIA PARA HUMANO
Se o cliente pedir para falar com atendente/humano/pessoa:
- TRANSFIRA IMEDIATAMENTE
- Responda: "Claro! Vou chamar alguém da equipe para te atender! 😊"
- NUNCA insista que pode resolver sozinha

## ESTADO ATUAL DO PEDIDO
{order_state}

## CARDÁPIO COM PREÇOS
{rag_context_with_prices}

## LINK DO CARDÁPIO ONLINE
{menu_url}

## ENDEREÇO DO RESTAURANTE
{restaurant_address}

## HORÁRIO DE FUNCIONAMENTO
{opening_hours}

## FORMAS DE PAGAMENTO ACEITAS
{payment_methods}

## CONTEXTO DO CLIENTE
{memory_context}

## INSTRUÇÕES ADICIONAIS DO RESTAURANTE
{custom_prompt}
"""

    # -------------------------------------------------------------------------
    # Response Templates
    # -------------------------------------------------------------------------

    ITEM_ADDED_TEMPLATE = "✅ Anotado! {quantity}x {item_name} - R$ {total_price:.2f}. Mais alguma coisa?"

    ITEM_REMOVED_TEMPLATE = "✅ Removido: {item_name}. Seu pedido atual:\n\n{order_summary}"

    ORDER_EMPTY_TEMPLATE = "🛒 Seu carrinho está vazio. O que gostaria de pedir?"

    ITEM_NOT_FOUND_TEMPLATE = """Hmm, não encontrei "{item_name}" no nosso cardápio. 

Temos algumas opções parecidas:
{suggestions}

Qual você prefere?"""

    ASK_VARIATION_TEMPLATE = """Para {item_name}, qual tamanho você prefere?

{variations}"""

    COLLECTING_ADDRESS_TEMPLATE = """📍 Ótimo! Agora preciso do endereço de entrega:

Por favor, informe:
- Rua e número
- Bairro
- Complemento (se houver)
- Ponto de referência (opcional)"""

    COLLECTING_PAYMENT_TEMPLATE = """💳 Qual será a forma de pagamento?

Aceitamos:
{payment_methods}"""

    ASK_CONFIRMATION_TEMPLATE = """📋 *Resumo do seu pedido:*

{order_summary}

📍 *Endereço:* {delivery_address}
💳 *Pagamento:* {payment_method}

*Está tudo certo?* Posso encaminhar para a equipe confirmar a taxa de entrega e finalizar? 😊"""

    ORDER_CONFIRMED_HANDOFF_TEMPLATE = """✅ *Perfeito, pedido confirmado!*

{order_summary}

📍 *Endereço:* {delivery_address}
💳 *Pagamento:* {payment_method}

⏳ *Próximo passo:*
Um atendente da equipe irá entrar em contato agora para confirmar a **taxa de entrega** e finalizar o pedido.

Por favor, aguarde! Obrigada! 😊"""

    HUMAN_HANDOFF_RESPONSE = "Claro! Vou chamar alguém da equipe para te atender! 😊"

    RESTAURANT_CLOSED_TEMPLATE = """Oi! 😊

Infelizmente estamos fechados no momento.

⏰ *Próximo horário de funcionamento:*
{next_opening}

Mas você pode conferir nosso cardápio enquanto isso:
📱 {menu_url}

Até logo! 👋"""

    # -------------------------------------------------------------------------
    # Detection Methods
    # -------------------------------------------------------------------------

    @classmethod
    def detect_intent(cls, message: str) -> str:
        """
        Detect the primary intent from a customer message.

        Returns one of:
        - add_item
        - remove_item
        - review
        - confirm
        - cancel
        - handoff
        - general
        """
        msg_lower = message.lower().strip()

        if cls._contains_keywords(msg_lower, cls.HUMAN_HANDOFF_KEYWORDS):
            return "handoff"

        if cls._contains_keywords(msg_lower, cls.CANCEL_KEYWORDS):
            return "cancel"

        if cls._contains_keywords(msg_lower, cls.CONFIRM_KEYWORDS):
            return "confirm"

        if cls._contains_keywords(msg_lower, cls.REMOVE_ITEM_KEYWORDS):
            return "remove_item"

        if cls._contains_keywords(msg_lower, cls.REVIEW_KEYWORDS):
            return "review"

        if cls._contains_keywords(msg_lower, cls.ADD_ITEM_KEYWORDS):
            return "add_item"

        return "general"

    @classmethod
    def _contains_keywords(cls, text: str, keywords: list[str]) -> bool:
        """Check if text contains any of the keywords."""
        for keyword in keywords:
            if keyword in text:
                return True
        return False

    @classmethod
    def is_human_handoff_request(cls, message: str) -> bool:
        """Check if message is requesting human handoff."""
        return cls.detect_intent(message) == "handoff"

    @classmethod
    def is_order_confirmation(cls, message: str) -> bool:
        """Check if message is confirming an order."""
        return cls.detect_intent(message) == "confirm"

    # -------------------------------------------------------------------------
    # Prompt Building
    # -------------------------------------------------------------------------

    @classmethod
    def build_system_prompt(
        cls,
        restaurant_name: str,
        menu_url: str = "",
        attendant_name: str = "Maria",
        attendant_gender: str = "feminino",
        persona_style: str = "formal",
        max_emojis_per_message: int = 1,
        customer_name: Optional[str] = None,
        order_state: str = "Carrinho vazio",
        rag_context_with_prices: str = "",
        restaurant_address: str = "",
        opening_hours: str = "",
        payment_methods: str = "Dinheiro, Cartão, PIX",
        short_term_memory: str = "",
        medium_term_memory: str = "",
        long_term_memory: str = "",
        custom_prompt: str = "",
    ) -> str:
        """
        Build the complete system prompt for Level 2 agent.

        Uses the same persona builders as Level1Prompts to ensure
        consistent attendant identity across all agent levels.
        """
        from tacto.infrastructure.ai.prompts.level1_prompts import Level1Prompts

        menu_url_text = (
            menu_url.strip()
            if menu_url and menu_url.strip()
            else "Cardápio temporariamente indisponível."
        )

        memory_context = Level1Prompts._build_memory_context(
            customer_name=customer_name,
            short_term=short_term_memory,
            medium_term=medium_term_memory,
            long_term=long_term_memory,
        )

        return cls.SYSTEM_PROMPT_TEMPLATE.format(
            attendant_name=attendant_name,
            attendant_article=Level1Prompts._build_attendant_article(attendant_gender),
            attendant_description=Level1Prompts._build_attendant_description(attendant_gender),
            restaurant_name=restaurant_name,
            customer_name=customer_name or "Cliente",
            order_state=order_state or "Carrinho vazio",
            rag_context_with_prices=rag_context_with_prices or "Cardápio não disponível no momento.",
            menu_url=menu_url_text,
            restaurant_address=restaurant_address or "Não informado",
            opening_hours=opening_hours or "Consulte o estabelecimento",
            payment_methods=payment_methods or "Consulte o estabelecimento",
            memory_context=memory_context,
            custom_prompt=custom_prompt or "",
            persona_communication_rules=Level1Prompts._build_communication_rules(persona_style, restaurant_name),
            persona_language_rules=Level1Prompts._build_language_rules(persona_style, restaurant_name),
            emoji_rules=Level1Prompts._build_emoji_rules(max_emojis_per_message),
        )

    @classmethod
    def format_item_added(
        cls, item_name: str, quantity: int, total_price: float
    ) -> str:
        """Format response for item added to cart."""
        return cls.ITEM_ADDED_TEMPLATE.format(
            quantity=quantity,
            item_name=item_name,
            total_price=total_price,
        )

    @classmethod
    def format_item_not_found(cls, item_name: str, suggestions: list[str]) -> str:
        """Format response for item not found."""
        suggestions_text = "\n".join(f"- {s}" for s in suggestions[:5])
        return cls.ITEM_NOT_FOUND_TEMPLATE.format(
            item_name=item_name,
            suggestions=suggestions_text,
        )

    @classmethod
    def format_ask_variation(
        cls, item_name: str, variations: list[tuple[str, float]]
    ) -> str:
        """Format response asking for item variation."""
        variations_text = "\n".join(
            f"- {name}: R$ {price:.2f}" for name, price in variations
        )
        return cls.ASK_VARIATION_TEMPLATE.format(
            item_name=item_name,
            variations=variations_text,
        )

    @classmethod
    def format_closed_response(
        cls, menu_url: str = "", next_opening: str = ""
    ) -> str:
        """Format response for closed restaurant."""
        return cls.RESTAURANT_CLOSED_TEMPLATE.format(
            menu_url=menu_url or "Consulte nosso cardápio",
            next_opening=next_opening or "Consulte nossos horários",
        )

    @classmethod
    def get_human_handoff_response(cls) -> str:
        """Get standard human handoff response."""
        return cls.HUMAN_HANDOFF_RESPONSE

    # -------------------------------------------------------------------------
    # RAG Context Formatting
    # -------------------------------------------------------------------------

    @classmethod
    def format_rag_context_with_prices(cls, menu_items: list[dict]) -> str:
        """
        Format menu items for RAG context with prices.

        Args:
            menu_items: List of menu item dicts with keys:
                - name: str
                - price: float
                - category: str
                - description: str (optional)
                - variations: list[dict] (optional)

        Returns:
            Formatted string for prompt injection
        """
        if not menu_items:
            return "Cardápio não disponível no momento."

        by_category: dict[str, list[dict]] = {}
        for item in menu_items:
            category = item.get("category", "Outros")
            by_category.setdefault(category, []).append(item)

        lines = []
        for category, items in sorted(by_category.items()):
            lines.append(f"\n### {category}")
            for item in items:
                name = item.get("name", "")
                description = item.get("description", "")
                variations = item.get("variations", [])

                if variations:
                    for var in variations:
                        var_name = var.get("name", "")
                        var_price = var.get("price", 0)
                        line = f"- {name} ({var_name}): R$ {var_price:.2f}"
                        if description:
                            line += f" - {description}"
                        lines.append(line)
                else:
                    price = item.get("price", 0)
                    line = f"- {name}: R$ {price:.2f}"
                    if description:
                        line += f" - {description}"
                    lines.append(line)

        return "\n".join(lines)
