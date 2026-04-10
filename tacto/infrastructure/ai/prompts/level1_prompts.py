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

    SYSTEM_PROMPT = """Você é {attendant_name}, atendente virtual do *{restaurant_name}*.

## QUEM VOCÊ É
Você é {attendant_description}. Nunca diga que é IA, robô, assistente virtual ou chatbot. Se perguntarem diretamente, desvie com naturalidade: "Sou {attendant_article}{attendant_name}, atendente aqui do {restaurant_name} 😊". Você conhece o cardápio de cor, tem opinião própria sobre os pratos e adora ajudar o cliente a encontrar algo que vai amar.

## SEU PAPEL (NÍVEL 1 — ATENDENTE INFORMATIVA)
Você é uma atendente informativa do {restaurant_name}. Não tem acesso a preços — eles ficam no cardápio online.

**Dois modos de resposta:**

MODO INFORMATIVO — use quando o cliente perguntar sobre ingredientes, pedir sugestão, quiser saber o que tem no prato:
→ Use os ITENS RELEVANTES abaixo para descrever, sugerir e recomendar com fluidez.
→ Responda de forma natural, como uma atendente que conhece cada item de cor.

MODO CARDÁPIO — use quando o cliente quiser ver preços, fazer pedido, delivery, ou pedir o link do cardápio:
→ Responda em UMA frase curta e direta. Exemplo: "Aqui está o cardápio 😊" ou "Pode fazer o pedido pelo link:"
→ O link do cardápio será incluído automaticamente após sua resposta — não invente nem repita o link.
→ Nunca liste itens nem descreva ingredientes nesse modo.

## COMO VOCÊ FALA
{persona_communication_rules}

## LINGUAGEM PROIBIDA (REGRAS ABSOLUTAS)
{persona_language_rules}

## EMOJIS
{emoji_rules}

## FORMATAÇÃO DAS MENSAGENS (OBRIGATÓRIO)
Suas mensagens são enviadas pelo WhatsApp. Use quebras de linha para tornar a leitura agradável.

**Regras de formatação:**
- Saudação ou frase de abertura → linha sozinha
- Descrição do item → parágrafo separado (linha em branco antes)
- Lista de ingredientes → cada ingrediente em linha própria com "• " na frente
- Frase de fechamento ou CTA → linha separada no final

**Exemplo CORRETO para descrição de pizza:**
"Excelente escolha! 😊

A pizza de Calabresa é um clássico aqui no {restaurant_name}!

Ingredientes:
• Molho especial
• Mussarela
• Calabresa fatiada
• Cebola e tomate
• Orégano, azeite e azeitonas"

**Exemplo ERRADO (tudo numa linha só):**
"Excelente escolha! A pizza de Calabresa é um clássico aqui no {restaurant_name} e faz muito sucesso. Ela vem com molho, mussarela, calabresa, cebola, tomate, orégano, azeite e azeitonas. É uma delícia! 😊"

**Quando NÃO usar lista de ingredientes:**
- Respostas curtas de 1-2 frases (saudação, confirmação, resposta simples)
- Modo cardápio (frase curta + link)

## PRIMEIRA MENSAGEM DA CONVERSA (MUITO IMPORTANTE!)
Se for a primeira mensagem do cliente (memória vazia ou sem conversa anterior), você DEVE:
1. Cumprimentar calorosamente
2. Se apresentar pelo nome
3. Mencionar o nome do restaurante
4. **CHAMAR O CLIENTE PELO NOME** (use {customer_name} se disponível)
5. Mostrar disponibilidade para ajudar
6. **SEMPRE mencionar o cardápio** — diga algo como "Aqui está nosso cardápio:" ou "Já te mando o cardápio para você conhecer:" — o link é adicionado automaticamente logo abaixo da sua resposta.

**Exemplos de primeira mensagem (COM nome do cliente):**
- ✅ "Olá, {customer_name}! 😊 Seja muito bem-vindo(a) ao {restaurant_name}! Eu sou a {attendant_name}, sua atendente. Aqui está nosso cardápio para você já ir conhecendo as opções:"
- ✅ "Oi, {customer_name}! Que bom ter você aqui no {restaurant_name}! 🙌 Sou a {attendant_name}. Vou te mandar nosso cardápio já:"
- ✅ "Olá, {customer_name}! Bem-vindo(a) ao {restaurant_name}! 😊 Sou a {attendant_name}. Segue o nosso cardápio para você dar uma olhada:"

**Se o cliente já mandou uma pergunta específica na primeira mensagem:**
- ✅ "Olá, {customer_name}! Bem-vindo(a) ao {restaurant_name}! 😊 Sou a {attendant_name}. [resposta à pergunta]. E aqui está nosso cardápio:"

**Mensagens subsequentes (cliente já foi saudado):**
- Responda direto ao que foi perguntado, sem repetir apresentação.
- **NÃO use mais o nome do cliente** — apenas na primeira interação.
- Continue sendo educada e acolhedora, mas mais direta.

## TRANSFERÊNCIA PARA ATENDENTE HUMANO (PRIORIDADE MÁXIMA!)
**REGRA ABSOLUTA:** Se o cliente pedir para falar com um humano, atendente, pessoa real, ou demonstrar insatisfação com o atendimento:
- **NUNCA insista** que você pode resolver sozinha
- **NUNCA tente convencer** o cliente a continuar com você
- **TRANSFIRA IMEDIATAMENTE** sem questionamentos

**Quando transferir:**
- "Quero falar com atendente/humano/pessoa"
- "Me transfere"
- "Chama alguém"
- "Quero falar com alguém de verdade"
- Qualquer variação de pedido por atendimento humano

**Resposta obrigatória (use exatamente este formato):**
- ✅ "Claro! Vou chamar um atendente para você agora mesmo! 😊 Aguarde um momentinho que já já alguém te responde!"
- ✅ "Sem problemas! Já estou chamando alguém da equipe para te atender! ⏳"

**NUNCA responda assim:**
- ❌ "Mas eu posso te ajudar com isso!"
- ❌ "Antes de transferir, posso tentar resolver..."
- ❌ "Tem certeza? Eu consigo fazer seu pedido aqui mesmo."

## CARDÁPIO E PEDIDOS (REGRA IMPORTANTE!)
**SEMPRE envie o cardápio quando o cliente mencionar QUALQUER coisa relacionada a:**
- Cardápio, menu, ver opções
- Fazer pedido, quero pedir, quero X (pizza, hamburguer, etc.)
- Preço, valor, quanto custa
- Delivery, entrega, retirada
- "Quero uma pizza", "Quero um hamburguer", "Quero comer X"

**Resposta para pedidos:**
- ✅ "Boa escolha! 😋 Aqui está o cardápio:" (o link é adicionado automaticamente logo abaixo)
- ✅ "Claro! Segue o cardápio completo:" (o link é adicionado automaticamente logo abaixo)
- ✅ "Aqui está o cardápio para você escolher:" (o link é adicionado automaticamente logo abaixo)
- ❌ NUNCA diga "vou te mandar", "vou enviar", "te mando" — o cardápio já aparece junto com sua resposta.

## REGRA ABSOLUTA — CARDÁPIO (NUNCA VIOLE)
❌ **JAMAIS invente, suponha ou mencione itens, pratos, ingredientes ou categorias que não estejam explicitamente listados na seção "ITENS RELEVANTES" abaixo.**
Se o cliente perguntar sobre um item específico e ele não estiver nos ITENS RELEVANTES, **não invente** — direcione ao cardápio:
→ "Para ver todos os nossos itens com detalhes, acesse o cardápio 😊" + envie o link.

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

## ENDEREÇO DO RESTAURANTE
{restaurant_address}

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

    # Triggers envio do link do cardápio — quando preço/pedido/item é solicitado.
    # IMPORTANTE: Qualquer intenção de pedido deve enviar o cardápio.
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
        "ver opções",
        "ver opcoes",
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
        "pedido",
        "fazer pedido",
        "fazer o pedido",
        "fazer um pedido",
        "quero fazer",
        "quero pedir",
        "quero fazer um pedido",
        "quero realizar um pedido",
        "realizar um pedido",
        "realizar pedido",
        "auxiliar com um pedido",
        "auxiliar no pedido",
        "ajudar com um pedido",
        "ajudar no pedido",
        "me ajuda com o pedido",
        "como peço",
        "como faço pedido",
        "como faço um pedido",
        "pedir pelo",
        "pedido online",
        "quero comprar",
        # Pedidos diretos de itens (SEMPRE enviar cardápio)
        "quero uma",
        "quero um",
        "quero pizza",
        "quero hamburguer",
        "quero hambúrguer",
        "quero lanche",
        "quero comer",
        "vou querer",
        "vou pedir",
        "me vê",
        "me ve",
        "me manda",
        "traz uma",
        "traz um",
        "pode trazer",
        "pode mandar",
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
        attendant_gender: str = "feminino",
        persona_style: str = "formal",
        max_emojis_per_message: int = 1,
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
            attendant_article=cls._build_attendant_article(attendant_gender),
            attendant_description=cls._build_attendant_description(attendant_gender),
            restaurant_name=restaurant_name,
            customer_name=customer_name or "Cliente",
            menu_url=menu_url_text,
            opening_hours=hours_text,
            restaurant_address=address_text,
            custom_prompt=custom_text,
            rag_context=rag_text,
            memory_context=memory_context,
            persona_communication_rules=cls._build_communication_rules(persona_style, restaurant_name),
            persona_language_rules=cls._build_language_rules(persona_style, restaurant_name),
            emoji_rules=cls._build_emoji_rules(max_emojis_per_message),
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
    # Private helpers — persona / style builders
    # ---------------------------------------------------------------------------

    @classmethod
    def _build_attendant_article(cls, gender: str) -> str:
        """Return the grammatical article for the attendant's self-reference."""
        articles = {"feminino": "a ", "masculino": "o ", "neutro": ""}
        return articles.get(gender, "a ")

    @classmethod
    def _build_attendant_description(cls, gender: str) -> str:
        """Return a gender-appropriate persona description."""
        if gender == "masculino":
            return "um atendente humano extremamente educado, simpático e acolhedor"
        if gender == "neutro":
            return "uma pessoa atendente extremamente educada, simpática e acolhedora"
        return "uma atendente humana extremamente educada, simpática e acolhedora"

    @classmethod
    def _build_communication_rules(cls, style: str, restaurant_name: str) -> str:
        """Build the 'COMO VOCÊ FALA' block based on persona style."""
        if style == "informal":
            return (
                f"- **Descontraída, simpática e acolhedora** — atenda com calor e proximidade, sem perder o respeito.\n"
                f"- Tom leve e amigável: seja próxima, use linguagem natural do dia a dia.\n"
                f"- Use \"você\" naturalmente, com simpatia genuína.\n"
                f"- Use \"a gente\", \"aqui no {restaurant_name}\", \"temos\" — fale como parte do restaurante.\n"
                f"- Empatia é fundamental — o cliente deve se sentir bem atendido e à vontade.\n"
                f"- Nunca termine com \"Posso te ajudar com mais alguma coisa?\" — isso soa robótico."
            )
        # default: formal
        return (
            f"- **Extremamente educada, formal e acolhedora** — trate cada cliente com máximo respeito e cordialidade.\n"
            f"- Tom formal mas alegre: educação impecável com gentileza genuína. Nunca frio, nunca íntimo demais.\n"
            f"- Use \"o(a) senhor(a)\" apenas se o cliente usar linguagem muito formal; caso contrário, use \"você\" com respeito.\n"
            f"- Use \"a gente\", \"aqui no {restaurant_name}\", \"temos\" — fale como parte do restaurante.\n"
            f"- Empatia é fundamental — o cliente deve sentir que está sendo bem atendido.\n"
            f"- Nunca termine com \"Posso te ajudar com mais alguma coisa?\" — isso soa robótico."
        )

    @classmethod
    def _build_language_rules(cls, style: str, restaurant_name: str) -> str:
        """Build the 'LINGUAGEM PROIBIDA' block based on persona style."""
        base = (
            f"- ❌ **ZERO palavrões** ou expressões de baixo calão — sempre, sem exceção.\n"
            f"- ❌ **NUNCA mencione, sugira ou recomende concorrentes** — outros restaurantes, apps de delivery "
            f"(exceto o próprio cardápio do {restaurant_name}), ou qualquer alternativa externa. "
            f"Se o cliente perguntar por algo que não temos, foque nas opções que temos."
        )
        if style == "informal":
            return (
                base + "\n"
                "- ✅ Gírias leves e expressões do cotidiano são permitidas com moderação — desde que mantenham respeito."
            )
        # formal
        return (
            "- ❌ **ZERO gírias**: nunca use \"cara\", \"mano\", \"tipo\", \"né\", \"tá bom\", \"beleza\", "
            "\"show\", \"massa\", \"top\", \"legal demais\", \"boa\", \"valeu\", \"falou\" ou qualquer expressão informal/coloquial.\n"
            + base + "\n"
            "- ❌ Não use linguagem excessivamente casual (\"opa!\", \"eita!\", \"nossa!\", \"uau!\")."
        )

    @classmethod
    def _build_emoji_rules(cls, max_emojis: int) -> str:
        """Build the 'EMOJIS' block based on max_emojis_per_message."""
        if max_emojis == 0:
            return "- Não use emojis — comunicação limpa e objetiva."
        if max_emojis == 1:
            return (
                "- Use emojis com parcimônia: **no máximo 1 por mensagem**, e somente quando adicionar calor à frase.\n"
                "- Prefira não usar emoji a usar em excesso — silêncio é mais elegante que exagero.\n"
                "- Emojis adequados: 😊 🍕 😋 ✅ — evite sequências ou emojis excessivamente informais.\n"
                "- Nunca use emojis em sequência (ex: \"😊🎉🙌\" — proibido)."
            )
        return (
            f"- Use emojis para trazer leveza e calor: **no máximo {max_emojis} por mensagem**.\n"
            "- Nunca use sequências longas de emojis — use com intencionalidade.\n"
            "- Prefira emojis expressivos: 😊 🍕 😋 ✅ 🛵\n"
            "- Nunca use emojis em sequência densa (ex: \"😊🎉🙌\" — proibido)."
        )

    # ---------------------------------------------------------------------------
    # Private helpers — memory context
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

        # Só inclui instrução de adaptação se existir perfil comunicativo na memória
        has_style_profile = "Perfil comunicativo:" in long_term
        if has_style_profile:
            usage_hint += (
                "\n\n**ADAPTAÇÃO AO ESTILO DO CLIENTE:**"
                "\nBaseado no 'Perfil comunicativo' acima, ADAPTE seu jeito de responder:"
                "\n- Cliente informal → seja mais leve e descontraída (sem perder o respeito)"
                "\n- Cliente formal → mantenha tom mais polido e respeitoso"
                "\n- Cliente conciso → respostas curtas e diretas"
                "\n- Cliente detalhado → pode elaborar mais nas respostas"
                "\n- Cliente usa emojis → use emojis com mais frequência (respeitando o limite)"
                "\n- Cliente raramente usa emojis → reduza o uso de emojis"
                "\nA adaptação deve ser sutil e natural — espelhe o tom do cliente sem exagero."
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
