def print_report(store):
    print("=" * 70)
    print("EnergIA — Rapport de chargement des données")
    print("=" * 70)
    print(f"Jeu de données : {store.metadata.get('dataset_name', 'inconnu')}")
    print(f"Version        : {store.metadata.get('version', '?')}")
    print()
    print(f"Centrales chargées : {len(store.centrales)}")
    print(f"Régions chargées   : {len(store.regions)}")
    print(f"Liaisons chargées  : {len(store.liaisons)}")
    print(f"Graphe             : {store.graph}")
    print(f"Puissance installée totale : "
          f"{sum(c.installed_power_mw for c in store.centrales.values()):.0f} MW")
    print()

    print("-- Exemple de centrale --")
    exemple_centrale = next(iter(store.centrales.values()))
    print(f"  {exemple_centrale}")
    print()

    print("-- Exemple de région --")
    exemple_region = next(iter(store.regions.values()))
    print(f"  {exemple_region}")
    print()

    print("-- Exemple de liaison --")
    if store.liaisons:
        print(f"  {store.liaisons[0]}")
    print()

    print("-- Exemple de chemin (Dijkstra) --")
    distance, chemin = store.graph.shortest_path("flamanville", "tricastin")
    if chemin:
        print(f"  flamanville -> tricastin : {' -> '.join(chemin)} ({distance:.1f} km)")
    else:
        print("  flamanville -> tricastin : aucun chemin trouvé")

    distance, chemin = store.graph.shortest_path("flamanville", "centrale_inconnue")
    if chemin:
        print(f"  flamanville -> centrale_inconnue : {' -> '.join(chemin)} ({distance:.1f} km)")
    else:
        print("  flamanville -> centrale_inconnue : aucun chemin trouvé")
    print()

    anomalies = store.verify()
    print("-" * 70)
    if anomalies:
        print(f"⚠️  {len(anomalies)} anomalie(s) détectée(s) :")
        for a in anomalies:
            print(f"   - {a}")
    else:
        print("✅ Aucune anomalie détectée : les données sont cohérentes.")
    print("=" * 70)
