import random

class Combattant:

    def __init__(self, nom, niveau, vie):

        self.nom = nom
        self.niveau = niveau
        self.vie = vie

    def se_presenter(self):

        print(
            f"{self.nom} "
            f"Niveau {self.niveau} "
            f"PV : {self.vie}"
        )

    def subir_degats(self, quantite):

        self.vie -= quantite

        if self.vie < 0:
            self.vie = 0

        print(
            f"{self.nom} subit "
            f"{quantite} dégâts."
        )

    def est_vivant(self):

        return self.vie > 0

    def attaquer(self, cible):

        degats = random.randint(1, 6)

        print(
            f"{self.nom} attaque "
            f"{cible.nom}"
        )

        cible.subir_degats(degats)