### ⚠️ Info: le projet est suspendu. Voici un récap de la situation au 29/10/2025:


# 1. Description du projet

Développé par des bénévoles de [Data For Good](https://www.dataforgood.fr/) lors de la saison 13 et porté par [Groupe SOS](https://www.groupe-sos.org/), ce projet vise à construire une solution d'IA générative afin d'assister la réponse des associations aux appels à projets des bailleurs de fonds publics et privés, une source clé de financement de leurs initiatives d'intérêt général. 

Open source et accessible à toutes les associations dans le besoin, la solution va leur permettre de se concentrer sur les aspects stratégiques et qualitatifs de leur activité, en automatisant les tâches les plus chronophages et en facilitant le reste.

# 2. Livrable

En utilisant la technique de RAG, le prototype livré à la fin de la saison 13 en Avril 2025 a bâti une application web Streamlit capable de pré-remplir un appel à projets d'un bailleur à partir des informations contenues dans les documents de projet et d'association fournis par l'utilisateur. Dotée des trois fonctionnalités suivantes, l'application prend en charge des documents en français et en anglais.

## 2.1. Chargement des documents sources via une interface web
- Une fiche du projet: elle contient les informations nécessaires liées au projet qui fait l'objet de la demande de financement 
- Un formulaire d'appel à projets vierge d'un bailleur de fonds: il s'agit du dossier de candidature à remplir par l'association, porteuse du projet à financer et utilisateur de l'application
- Une présentation de l'association: elle contient les informations nécessaires liées à l'association, porteuse du projet à financer et utilisateur de l'application

## 2.2. Visualisation du formulaire d'appel à projets pré-rempli par l'IA

## 2.3. Téléchargement du formulaire d'appel à projets pré-rempli pour rectification manuelle ou soumission au bailleur


Ce prototype étant validé par [Groupe SOS](https://www.groupe-sos.org/), nous poursuivons actuellement son amélioration (notamment l'UI, l'extraction des contextes spécifiques et la pertinence des réponses) afin de livrer un MVP en Septembre 2025.

# 3. Architectures

## 3.1. Architecture de la solution
![architecture](https://github.com/user-attachments/assets/3720ccf1-5ea1-4134-81ea-e5378c4e54ed)

## 3.2. Architecture d'optimisation de RAG
![rag](https://github.com/user-attachments/assets/661ccc88-17e5-4c32-9655-c12622eba652)

# 4. Contributing

## 4.1. Pour commencer
### 4.1.1. [Rejoindre](https://dataforgood.fr/join) la communauté Data For Good
### 4.1.2. Sur le slack Data For Good, rejoindre le canal #13_ia_financement et se présenter
### 4.1.3. Remplir le [formulaire](https://noco.services.dataforgood.fr/dashboard/#/nc/form/895fb8bb-df66-495a-b806-6a1d49a514f3)
### 4.1.4. Demander un accès en écriture si je souhaite proposer une modification du code

## 4.2. Après avoir été affecté à une tâche
### 4.2.1. Cloner le projet en local :
```bash
    git clone https://github.com/dataforgoodfr/13_ia_financement
```
### 4.2.2. Si ca fait un moment que le projet a été cloné, s'assurer d'être à jour avec le code :
```bash
    git checkout main
    git pull origin main
```
### 4.2.3. Créer une branche avec un nom qui facilitera le lien avec une tâche du projet :
```bash
    git checkout -b <branch-name>
```
Pour le nom de la branche :
- si c'est une évolution du code : feature/<titre_de_la_fonctionnalite>
- si c'est pour corriger un bug : fix/<titre_du_bug>

## 4.3. Pendant la réalisation de la tâche
### 4.3.1. Essayer d'avoir des messages de commit le plus clairs possibles :
```bash
    git add script_modifie.py
    git commit -m "<description de la modification>"
```
### 4.3.2. Ne jamais commit directement sur main !

## 4.4. Une fois la tâche terminée
### 4.4.1. Push sa branche :
```bash
    git push -u origin <branch-name>
```
### 4.4.2. Créer une pull request sur [github](https://github.com/dataforgoodfr/13_ia_financement/compare)
### 4.4.3. Demander une review et une validation de la PR pour qu'elle soit merge sur main
### 4.4.4. Une liste de verifications pour faciliter la validation est disponible dans ce [template](.github/pull_request_template.md)

# 5. Installation

## 5.1. Installer Poetry

Plusieurs [méthodes d'installation](https://python-poetry.org/docs/#installation) sont décrites dans la documentation de poetry dont:

- avec pipx
- avec l'installateur officiel

Chaque méthode a ses avantages et inconvénients. Par exemple, la méthode pipx nécessite d'installer pipx au préable, l'installateur officiel utilise curl pour télécharger un script qui doit ensuite être exécuté et comporte des instructions spécifiques pour la completion des commandes poetry selon le shell utilisé (bash, zsh, etc...).

L'avantage de pipx est que l'installation de pipx est documentée pour linux, windows et macos. D'autre part, les outils installées avec pipx bénéficient d'un environment d'exécution isolé, ce qui est permet de fiabiliser leur fonctionnement. Finalement, l'installation de poetry, voire d'autres outils est relativement simple avec pipx.

Cependant, libre à toi d'utiliser la méthode qui te convient le mieux ! Quelque soit la méthode choisie, il est important de ne pas installer poetry dans l'environnement virtuel qui sera créé un peu plus tard dans ce README pour les dépendances de la base de code de ce repo git.

### 5.1.1. Installation de Poetry avec pipx

Suivre les instructions pour [installer pipx](https://pipx.pypa.io/stable/#install-pipx) selon ta plateforme (linux, windows, etc...)

Par exemple pour Ubuntu 23.04+:

    sudo apt update
    sudo apt install pipx
    pipx ensurepath

[Installer Poetry avec pipx](https://python-poetry.org/docs/#installing-with-pipx):

    pipx install poetry

### 5.1.2. Installation de Poetry avec l'installateur officiel

L'installation avec l'installateur officiel nécessitant quelques étapes supplémentaires,
se référer à la [documentation officielle](https://python-poetry.org/docs/#installing-with-the-official-installer).

## 5.2. Utiliser un venv python

    python3 -m venv .venv

    source .venv/bin/activate

## 5.3. Utiliser Poetry

Installer les dépendances:

    poetry install

Ajouter une dépendance:

    poetry add pandas

Mettre à jour les dépendances:

    poetry update

## 5.4. Lancer les precommit-hook localement

[Installer les precommit](https://pre-commit.com/)

    pre-commit run --all-files

## 5.5. Utiliser Tox pour tester votre code

    tox -vv
