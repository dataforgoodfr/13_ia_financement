# IA pour répondre aux appels à projets

Développé par des bénévoles de [Data For Good](https://www.dataforgood.fr/) lors de la saison 13 et porté par [Groupe SOS](https://www.groupe-sos.org/), ce projet vise à construire une solution d'intelligence artificielle pour faciliter la réponse des associations aux appels à projets publics et privés, une source clé de leur financement. La solution va leur permettre de se concentrer sur des aspects stratégiques et qualitatifs de leur activité, en automatisant les tâches les plus chronophages. 

# Livrables

- Une interface web permettant le chargement des documents et la visualisation des résultats
- Un modèle d'IA générative open source pour le remplissage automatique des formulaires (POC + MVP)
- Un livre blanc sur les bonnes pratiques d'utilisation de l'IA dans ce contexte

# Contributing

## Pour commencer
1. [Rejoindre](https://dataforgood.fr/join) la communauté Data For Good
2. Sur le slack Data For Good, rejoindre le canal _#13_potentiel_solaire_ et se présenter
3. Remplir le [formulaire](https://noco.services.dataforgood.fr/dashboard/#/nc/form/895fb8bb-df66-495a-b806-6a1d49a514f3)
4. Demander un accès en écriture si je souhaite proposer une modification du code

## Après avoir été affecté à une tâche
1. Cloner le projet en local :
```bash
    git clone https://github.com/dataforgoodfr/13_ia_financement
```
2. Si ca fait un moment que le projet a été cloné, s'assurer d'être à jour avec le code :
```bash
    git checkout main
    git pull origin main
```
3. Créer une branche avec un nom qui facilitera le lien avec une tâche du projet :
```bash
    git checkout -b <branch-name>
```
Pour le nom de la branche :
- si c'est une évolution du code : feature/<titre_de_la_fonctionnalite>
- si c'est pour corriger un bug : fix/<titre_du_bug>

## Pendant la réalisation de la tâche
1. Essayer d'avoir des messages de commit le plus clairs possibles :
```bash
    git add script_modifie.py
    git commit -m "<description de la modification>"
```
2. Ne jamais commit directement sur main !

## Une fois la tâche terminée
1. Push sa branche :
```bash
    git push -u origin <branch-name>
```
2. Créer une pull request sur [github](https://github.com/dataforgoodfr/13_ia_financement/compare)
3. Demander une review et une validation de la PR pour qu'elle soit merge sur main
4. Une liste de verifications pour faciliter la validation est disponible dans ce [template](.github/pull_request_template.md)

# Installation

## Installer Poetry

Plusieurs [méthodes d'installation](https://python-poetry.org/docs/#installation) sont décrites dans la documentation de poetry dont:

- avec pipx
- avec l'installateur officiel

Chaque méthode a ses avantages et inconvénients. Par exemple, la méthode pipx nécessite d'installer pipx au préable, l'installateur officiel utilise curl pour télécharger un script qui doit ensuite être exécuté et comporte des instructions spécifiques pour la completion des commandes poetry selon le shell utilisé (bash, zsh, etc...).

L'avantage de pipx est que l'installation de pipx est documentée pour linux, windows et macos. D'autre part, les outils installées avec pipx bénéficient d'un environment d'exécution isolé, ce qui est permet de fiabiliser leur fonctionnement. Finalement, l'installation de poetry, voire d'autres outils est relativement simple avec pipx.

Cependant, libre à toi d'utiliser la méthode qui te convient le mieux ! Quelque soit la méthode choisie, il est important de ne pas installer poetry dans l'environnement virtuel qui sera créé un peu plus tard dans ce README pour les dépendances de la base de code de ce repo git.

### Installation de Poetry avec pipx

Suivre les instructions pour [installer pipx](https://pipx.pypa.io/stable/#install-pipx) selon ta plateforme (linux, windows, etc...)

Par exemple pour Ubuntu 23.04+:

    sudo apt update
    sudo apt install pipx
    pipx ensurepath

[Installer Poetry avec pipx](https://python-poetry.org/docs/#installing-with-pipx):

    pipx install poetry

### Installation de Poetry avec l'installateur officiel

L'installation avec l'installateur officiel nécessitant quelques étapes supplémentaires,
se référer à la [documentation officielle](https://python-poetry.org/docs/#installing-with-the-official-installer).

## Utiliser un venv python

    python3 -m venv .venv

    source .venv/bin/activate

## Utiliser Poetry

Installer les dépendances:

    poetry install

Ajouter une dépendance:

    poetry add pandas

Mettre à jour les dépendances:

    poetry update

## Lancer les precommit-hook localement

[Installer les precommit](https://pre-commit.com/)

    pre-commit run --all-files

## Utiliser Tox pour tester votre code

    tox -vv
