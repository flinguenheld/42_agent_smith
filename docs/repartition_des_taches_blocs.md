# Organisation d'Équipe & Feuille de Route

Dans cette partie, nous voyons comment décomposer concrètement le projet **Agent Smith** pour travailler efficacement en binôme :

1. **Une approche de répartition du travail** (Division par Blocs) ;
2. **Une feuille de route (*****Roadmap*****) séquentielle** pour savoir exactement dans quel ordre attaquer les briques techniques sans se disperser.

***

## Rôles

| Rôle                       | Périmètre                                                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **D1 : L'Orchestrateur**   | Interfaçage avec les API LLM, parsing multi-format, rotation des clés API, boucle `Thought → Code → Observation`, prompt système, benchmark.    |
| **D2 : La Sandbox**        | Environnement Python restreint (CLI REPL + moteur d'exécution), contrôle des ressources, analyse AST, isolation des chemins, client MCP interne.|
| **D3 : Écosystème MCP & Outils** (D1 + D2 en commun) | Serveurs MCP (`stdio` et `HTTP`), outils de fichiers / recherche de code / tests, conteneurs Docker SWE-bench.        |

***

## 1. Plan de répartition du travail à 2

### Approche : Division par Blocs (Fonctionnalités de bout en bout)

Plutôt que de séparer le travail uniquement par couche technique isolée (au risque que chacun code dans son coin pendant 3 semaines sans pouvoir rien tester ensemble), l'équipe avance par **paliers fonctionnels** de complexité croissante.

### Sprint 1 : Le MVP MBPP

**Objectif :** Validation du concept central et premier succès de bout en bout sur une tâche algorithmique simple.

**D1 — Orchestrateur**

- [ ] Boucle itérative basique
- [ ] Prompt initial

**D2 — Sandbox**

- [ ] Mécanisme `exec()` isolé basique
- [ ] `final_answer()`
- [ ] Capture `stdout` / `stderr`

**D3 — MCP & Outils (en commun)**

- [ ] Premier outil `run_tests` pour MBPP

**Livrable :**

- [ ] Un agent capable de lire un fichier JSON MBPP, de générer du code, de lancer les tests et de produire une première solution valide.

### Sprint 2 : Sécurisation & Standardisation MCP

**Objectif :** Respect strict des normes du sujet, implémentation de la sécurité Sandbox et du protocole MCP complet.

**D1 — Orchestrateur**

- [ ] Implémentation complète de `StepMetrics`
- [ ] Implémentation complète de `SolutionOutput`
- [ ] Rotation de clés
- [ ] Parseur multi-format

**D2 — Sandbox**

- [ ] Analyse AST
- [ ] Blocage des builtins
- [ ] Blocage des imports
- [ ] Blocage des chemins
- [ ] Blocage du réseau
- [ ] Timeouts
- [ ] REPL `uv run sandbox`

**D3 — MCP & Outils (en commun)**

- [ ] Serveur `mcp_tools_mbpp.py` en `stdio`
- [ ] Serveur `mcp_tools_mbpp.py` en `HTTP`
- [ ] Découverte dynamique

**Livrables :**

- [ ] Une architecture résiliente et sécurisée qui valide `exam_sandbox.sh`
- [ ] … et `exam_mbpp.sh` (≥ 4/5)

### Sprint 3 : L'Épreuve SWE-bench & Benchmark

**Objectif :** Confrontation aux dépôts réels dans Docker, navigation dans le code et campagne de benchmark multi-modèles.

**D1 — Orchestrateur**

- [ ] Optimisation du prompt SWE-bench
- [ ] Gestion des contextes longs (`300k` tokens)
- [ ] Campagne de tests des 5 modèles
- [ ] Rédaction de `BENCHMARK_REPORT.md`

**D2 — Sandbox**

- [ ] Intégration de la Sandbox avec le workflow Docker
- [ ] Feedbacks d'erreur avancés

**D3 — MCP & Outils (en commun)**

- [ ] Serveur `mcp_tools_swebench.py` avec les 9 outils obligatoires
- [ ] Gestion propre du cycle de vie des conteneurs Docker

**Livrables :**

- [ ] Résolution autonome d'Issues GitHub réelles (≥ 2/3 sur `exam_swebench.sh`)
- [ ] Génération de patchs Git propres
- [ ] Rapport d'évaluation complet

#### But de cette approche

L'équipe dispose **en permanence d'une version fonctionnelle et testable de bout en bout**, ce qui élimine l'effet tunnel. Dès la fin du Sprint 1, l'agent tourne sur MBPP ; le Sprint 2 verrouille la sécurité et le standard MCP ; le Sprint 3 concentre toute l'énergie sur le défi majeur du SWE-bench et l'étude comparative des modèles.

***

## 2. Feuille de route séquentielle (*Roadmap*)

Voici l'ordre logique recommandé pour construire le projet brique par brique sans se disperser :

### Étape 0 — Fondations de l'Infrastructure *(D1 + D2)*

Avant d'écrire la moindre ligne de code impliquant un appel réseau vers un LLM, l'infrastructure logicielle doit être posée proprement :

- [x] 1. Initialiser le dépôt avec **`uv`** et **Python 3.10** (exigences strictes du chapitre IV.1).
- [ ] 2. Configurer le fichier **`.env`** pour le chargement sécurisé des clés API et verrouiller immédiatement le **`.gitignore`** (pour exclure `.env`, caches, outputs générés et images).
- [ ] 3. Modéliser les structures de données en implémentant tous les **modèles Pydantic** exigés par le sujet : `SandboxConfig`, `MBPPTaskInput`, `SWEBenchTaskInput`, `StepMetrics` et `SolutionOutput`.

### Étape 1 — Prototype de la Sandbox Locale *(D2)*

Développer le cœur de la sandbox :

- [ ] 1. Une fonction isolée capable de recevoir une chaîne de code Python arbitraire, de vérifier son arbre syntaxique (`ast`), et de l'exécuter dans un namespace restreint (`__builtins__` filtrés, imports contrôlés par `authorized_imports`, accès fichiers restreint à `allowed_directories`, réseau coupé).
- [ ] 2. Capturer proprement les flux `stdout` et `stderr`, gérer le timeout (`30s`) et la limite RAM (`512 Mo`) via un processus isolé, et restituer des messages d'erreur explicites sans jamais faire crasher le processus parent.
- [ ] 3. Injecter la primitive native `final_answer()` et proposer le mode interactif REPL (`uv run sandbox`).

### Étape 2 — L'Orchestrateur et la Boucle Agentique *(D1)*

Déplacer l'effort vers le cerveau de l'agent :

- [ ] 1. Construire l'**extracteur de code multi-format** capable de traverser la réponse brute du LLM (`llm_output`) pour en extraire le code Python ou convertir les formats alternatifs (XML `<invoke>`, JSON/Hermes `<tool_call>`, ReAct `Action:`) en appels de fonctions Python.
- [ ] 2. Implémenter le **client LLM multi-provider** avec rotation fluide des clés API, *exponential backoff* sur les erreurs `429`/`5xx`, paramétrage des `stop_sequences`, et comptage précis des tokens et de la latence (`StepMetrics`).
- [ ] 3. Coupler cette boucle d'appels API avec la Sandbox pour valider les premières séquences autonomes `Thought → Code → Observation`.

### Étape 3 — Le Point de Bascule : Intégration du Protocole MCP *(D2 + D3 en commun)*

Connecter la Sandbox au monde extérieur :

- [ ] 1. Intégrer dans la Sandbox un **client MCP** supportant à la fois les transports **`stdio`** et **`Streamable HTTP`**. *(D2)*
- [ ] 2. Créer le premier serveur MCP (`mcp_tools_mbpp.py`) exposant `run_tests` pour valider le **handshake MCP** complet. *(D3 en commun)*
- [ ] 3. Exploiter la découverte dynamique (`tools/list`, `resources/list`, `prompts/list`) pour générer automatiquement le **Manuel de la Sandbox** injecté dans le prompt système du modèle, et exposer dynamiquement chaque outil MCP comme une fonction Python appelable dans le namespace de la sandbox. *(D2)*

### Étape 4 — L'Épreuve Terminale : SWE-bench, Docker & Benchmark Report *(D1 + D2)*

Attaquer la partie la plus ambitieuse du sujet :

- [ ] 1. Développer `mcp_tools_swebench.py` avec les **9 outils obligatoires** en soignant les formats de retour (`cat -n`, `grep`) et les messages d'erreur pour guider le LLM. *(D3 en commun)*
  - [ ] `read_file`
  - [ ] `edit_file`
  - [ ] `list_files`
  - [ ] `search_code`
  - [ ] `search_function_or_class_definition_in_code`
  - [ ] `find_references`
  - [ ] `run_tests`
  - [ ] `get_patch`
  - [ ] `run_command`
- [ ] 2. Intégrer la gestion des conteneurs Docker SWE-bench (montage ou accès à `${TESTBED_PATH}`, génération du diff via `git -c core.fileMode=false diff`, et **nettoyage systématique du conteneur** après exécution). *(D3 en commun)*
- [ ] 3. Tester et itérer d'abord sur les tâches recommandées par le sujet (`sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`) en inspectant les 3 à 5 premières itérations. *(D1)*
- [ ] 4. Lancer la campagne d'évaluation croisée d'au moins **5 modèles sur au moins 3 tâches SWE-bench**, conserver les fichiers `solution.json` correspondants et rédiger le **`BENCHMARK_REPORT.md`** ainsi que le **`README.md`** final en anglais. *(D1, README en commun)*
