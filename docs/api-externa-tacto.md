# API - TACTO

https://api-externa.tactonuvem.com.br/swagger/index.html

Passar no Header Sempre:

Tacto-Grupo-Empresarial → é a chave do grupo empresarial da empresa em questão dentro da nossa estrutura.

EmpresaId → é o codigo da empresa dentro do grupo.

chave-origem → Chave exclusiva para essa integração, extremamente importante, segredo.  Chave fixa que vai valer para todas empresas.
DA885FE3-44F8-46FE-BC8B-EF709F4EC2AA



Autenticação : Gerar um Token no metodo

https://accounts.tactonuvem.com.br/connect/token

O  client_secret => d59883992608430081c5a632b0619826

# Necessario para se conectar:

1)) Gostaria que o projeto se chamasse TactoFlow.

2)) Estruturação basica para controle das empresas.

a) Tabela TipoAutomacao, que seria uma tabela fixa para classificarmos as empresas, por mais que agora seja apenas 1.. ja temos que iniciar preparado.

Id  → Codigo do tipo, fixo sem auto incremento

Nome → Texto com nome.

(Cadastrar o primeiro registro ID = 1, Nome = “Food - Delivery”)

Tipos->

Food - Delivery

Food - Mesa e Comanda

b) OrigemIntegracao, tabela fix para sabermos de onde vem a integração.

Id  → Codigo do tipo, fixo sem auto incremento

Nome → Texto com nome.

Cadastrar:

ID 1 = Meta - Oficial

ID 2= Join Developer

c) Tabela EmpresaCanal, alem do basico, precisa ter esses campos:

TipoAutomacaoId → Vinculo com a tabela TipoAutomacao

OrigemId→ Vinculo com a tabela OrigemIntegracao

ChaveGrupoEmpresarial → GUID

EmpresaBaseId → Id da empresa dentro do grupo

CanalMasterId → Id do canal para referenciar com os dados que tenho.

## Nivel de Automacao:
Conforme haviamos planejado no inicio, já deve ter a Tabela TipoAutomacao, que seria para classificarmos as empresas. Agora vamos criar outra classificação, o Nivel de Automação. Para que possa configurar a forma basica de comportamento de cada empresa dentro do tipo.



Tipos->

Delivery Basico

Delivery Intermediario

Delivery Avançado

Delivery Basico

Deve conter o Rag com as informações institucionais.

Nesse modelo, o sistema irá responder apenas respostas institucionais da empresa, como horarios e endereço.

Deverá fazer:

Recepcionar o Cliente.

Sugerir o Link do Cardápio. ( Evitar enviar repetidamente sem o cliente perguntar)

Não podera fazer:

Passar informações dos produtos do cardápio.

Anotar Pedidos.

2)) Delivery Intermediario

Fazer tudo que o básico faz, porem deve conter o Rag do cardápio para responder coisas sobre os produtos, caso o cliente pergunte. Porém não deve anotar os pedidos, continue sugerindo o link do cardapio para realizar os pedidos.

3)) Delivery Avançado

Fazer tudo que o intermediario faz, acrescentando as funções de anotar o pedido e consumir o metodo post no momento certo.

# Regras basicas da Automacao: 
Pontos importantes :

Proibir Palavrões.

Proibir falar ou sugerir concorrencia.

Em Caso de detectar ação do usuario(funcionario da empresa), desativar o Bot por 12hr.

Agrupar as mensagens enviadas em menos de 5segundos para responder apenas 1 vez.

Não marcar a mensagem recebida para responde-la.

Tentar ser o maximo possivel formal, no entanto as respostas podem ser alegres, usar emotions com cuidado, porem não usar gírias informais.