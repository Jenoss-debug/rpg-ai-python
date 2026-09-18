from combattant import Combattant

class Joueur(Combattant):

    def __init__(self, nom, classe, niveau, vie):

        super().__init__(
            nom,
            niveau,
            vie
        )

        self.classe = classe

    def se_presenter(self):

        print(
            f"{self.nom} "
            f"({self.classe}) "
            f"Niveau {self.niveau} "
            f"PV : {self.vie}"
        )