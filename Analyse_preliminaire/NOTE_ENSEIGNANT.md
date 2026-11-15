# Brouillon de note à l'enseignant (non envoyée)

> 15/11/2026 · branche `modeles-premier-jet` · version `v0.1` · **Résultats provisoires et exploratoires, voir
> `STATUT_RESULTATS.md`** · aucun commit à ce stade. **À relire et valider par l'équipe avant tout envoi.**

Madame, Monsieur,

Nous vous signalons un changement de cap dans notre projet sur les sinistres d'inondation du NFIP. Notre
proposition portait sur la sévérité des sinistres et la prime pure. Nous étudions désormais la fréquence des
sinistres, car les données OpenFEMA caviardées ne fournissent aucune clé reliant un sinistre à sa police :
l'exposition ne peut être reliée aux sinistres qu'en agrégé, par comté, zone d'inondation et année. Notre
mise à jour du 16/11/2026 présente le nettoyage des données, une table d'analyse agrégée et une première
analyse exploratoire comparant des GLM (Poisson, binomial négatif) à LightGBM. Ces résultats sont
provisoires : ils reposent sur cinq années de test et sur une unité plus grossière que le secteur de
recensement que nous visons. Nous restons à votre disposition pour en discuter.

L'équipe : Lucas Jondeau, Lucas Lehmann, Nicolas Rohner, Pablo Villadoniga
