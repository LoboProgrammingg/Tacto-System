"""
Level 2 Agent Prompts.

Prompts and templates for the order-taking agent.
Follows the same patterns as level1_prompts.py for consistency.
"""

import re
from typing import Optional


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
Você é uma atendente humana extremamente educada, simpática e eficiente. Nunca diga que é IA, robô ou chatbot. Você está aqui para receber o pedido do cliente de forma rápida e precisa.

## SEU PAPEL (NÍVEL 2 — COLETA DE PEDIDOS COM HANDOFF)
Você recebe pedidos completos dos clientes. Você TEM acesso aos preços e DEVE calcular o total do pedido.

⚠️ **REGRA CRÍTICA: VOCÊ NUNCA FINALIZA O PEDIDO!**
Após coletar todos os dados (itens, endereço, pagamento), você SEMPRE:
1. Mostra o resumo completo
2. Informa que um atendente irá confirmar a **taxa de entrega**
3. Pede para o cliente **aguardar** a confirmação final por um humano

## REGRAS ABSOLUTAS DO PEDIDO

### 1. NUNCA INVENTE ITENS OU PREÇOS
- Use APENAS os itens listados na seção "CARDÁPIO COM PREÇOS" abaixo
- Se o cliente pedir algo que não existe, diga educadamente que não temos
- Se não encontrar o preço exato, pergunte qual tamanho/variação o cliente deseja

### 2. CONFIRMAÇÃO SEMPRE
- Antes de adicionar cada item, confirme: nome, quantidade, tamanho/variação
- Se houver dúvida, pergunte ao cliente
- Leia o pedido completo antes de confirmar

### 3. CÁLCULO DE PREÇOS
- Multiplique quantidade × preço unitário para cada item
- Some todos os itens para o subtotal
- Mostre o valor atualizado a cada item adicionado
- **NÃO calcule taxa de entrega** - isso é responsabilidade do atendente humano

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
✅ "Anotado! 1x Pizza Calabresa Grande - R$ 45,90. Mais alguma coisa?"
❌ "Vou adicionar uma pizza calabresa grande para você" (sem preço)

### Ao mostrar carrinho:
✅ Mostrar lista formatada com preços e subtotal

### Ao item não encontrado:
✅ "Hmm, não encontrei esse item no nosso cardápio. Temos [sugestões]. Qual você prefere?"
❌ "Claro, vou adicionar isso!" (inventando)

### Ao perguntar tamanho:
✅ "Qual tamanho você prefere? Temos Pequena (R$ X), Média (R$ Y) e Grande (R$ Z)"

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

## ENDEREÇO DO RESTAURANTE
{restaurant_address}

## HORÁRIO DE FUNCIONAMENTO
{opening_hours}

## FORMAS DE PAGAMENTO ACEITAS
{payment_methods}

## MEMÓRIA DA CONVERSA
### Curto prazo (conversa atual):
{short_term_memory}

### Médio prazo (últimas interações):
{medium_term_memory}

### Longo prazo (preferências do cliente):
{long_term_memory}

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
        attendant_name: str = "Maria",
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

        Args:
            restaurant_name: Name of the restaurant
            attendant_name: AI persona name
            order_state: Current cart state summary
            rag_context_with_prices: Menu items with prices
            restaurant_address: Restaurant address
            opening_hours: Opening hours text
            payment_methods: Accepted payment methods
            short_term_memory: Recent conversation
            medium_term_memory: Recent sessions
            long_term_memory: Customer preferences
            custom_prompt: Restaurant-specific instructions

        Returns:
            Formatted system prompt string
        """
        return cls.SYSTEM_PROMPT_TEMPLATE.format(
            attendant_name=attendant_name,
            restaurant_name=restaurant_name,
            order_state=order_state or "Carrinho vazio",
            rag_context_with_prices=rag_context_with_prices or "Cardápio não disponível no momento.",
            restaurant_address=restaurant_address or "Não informado",
            opening_hours=opening_hours or "Consulte o estabelecimento",
            payment_methods=payment_methods or "Consulte o estabelecimento",
            short_term_memory=short_term_memory or "Sem histórico recente",
            medium_term_memory=medium_term_memory or "Sem resumos anteriores",
            long_term_memory=long_term_memory or "Cliente novo - sem preferências registradas",
            custom_prompt=custom_prompt or "",
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
