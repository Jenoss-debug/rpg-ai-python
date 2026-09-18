from joueur import Joueur
from monstre import Monstre

thomas = Joueur(
    "Thomas",
    "Guerrier",
    8,
    45
)

gobelin = Monstre(
    "Gobelin",
    8,
    45
)

thomas.se_presenter()
gobelin.se_presenter()


print()
print("Le combat commence !")
print()

while gobelin.est_vivant() and thomas.est_vivant():

    thomas.attaquer(gobelin)

    if gobelin.est_vivant():
        gobelin.attaquer(thomas)

    thomas.se_presenter()
    gobelin.se_presenter()
    print()

    if not gobelin.est_vivant() :
        print("Thomas a gagné !")

    if not thomas.est_vivant() :
        print("Gobelin a gagné !")


