"""Проверки на искусственной сети: не доказательство социальных закономерностей."""
import json
import math
import sys
from importlib.metadata import version
from pathlib import Path
import networkx as nx


def validate_distances(graph, attribute="distance"):
    for u, v, data in graph.edges(data=True):
        value = data.get(attribute)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Нет числового расстояния на {u!r} -> {v!r}")
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Для взвешенной betweenness нужны положительные конечные расстояния")


def build_graph():
    G = nx.Graph()
    G.add_nodes_from(["A", "B", "C", "D", "isolate"])
    G.add_edge("A", "B", distance=1.0, strength=4.0)
    G.add_edge("B", "C", distance=1.0, strength=3.0)
    G.add_edge("A", "C", distance=5.0, strength=1.0)
    G.add_edge("C", "D", distance=2.0, strength=2.0)
    return G


def run(output_dir):
    print(json.dumps({"python": sys.version.split()[0], "networkx": version("networkx")}, ensure_ascii=False))
    G = build_graph()
    validate_distances(G)
    for bad in (None, 0, -1, float("nan"), float("inf"), True):
        H = G.copy()
        H["A"]["B"]["distance"] = bad
        try:
            validate_distances(H)
        except ValueError:
            pass
        else:
            raise AssertionError("Некорректное расстояние не отклонено")
    assert set(nx.isolates(G)) == {"isolate"}
    path = nx.shortest_path(G, "A", "C", weight="distance")
    length = nx.shortest_path_length(G, "A", "C", weight="distance")
    assert path == ["A", "B", "C"] and length == 2.0
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    largest = G.subgraph(components[0]).copy()
    assert nx.is_connected(largest) and not nx.is_connected(G)
    centrality = nx.betweenness_centrality(G, weight="distance", normalized=True)
    assert centrality["isolate"] == 0
    communities = list(nx.community.greedy_modularity_communities(largest, weight="strength", resolution=1.0))
    assert set().union(*communities) == set(largest)
    assert sum(map(len, communities)) == len(largest)
    q = nx.community.modularity(largest, communities, weight="strength", resolution=1.0)

    # Экспортируем только в явно заданный каталог, без перезаписи существующего файла.
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "synthetic.graphml"
    if target.exists():
        raise FileExistsError(f"Файл уже существует: {target}")
    nx.write_graphml(G, target)
    H = nx.read_graphml(target)
    assert G.is_directed() == H.is_directed() and G.is_multigraph() == H.is_multigraph()
    assert set(G) == set(H) and G.number_of_edges() == H.number_of_edges()
    assert set(nx.isolates(H)) == {"isolate"}
    for u, v, data in G.edges(data=True):
        assert H.has_edge(u, v)
        for attribute in ("distance", "strength"):
            assert math.isclose(data[attribute], H[u][v][attribute], rel_tol=1e-12, abs_tol=1e-12)
    validate_distances(H)
    assert nx.shortest_path_length(H, "A", "C", weight="distance") == length
    print(json.dumps({"synthetic_only": True, "nodes": len(G), "edges": G.number_of_edges(),
                      "isolates": list(nx.isolates(G)), "component_sizes": list(map(len, components)),
                      "path": path, "length": length, "betweenness_all_nodes": centrality,
                      "largest_component_coverage": len(largest)/len(G),
                      "mean_path_largest_only": nx.average_shortest_path_length(largest, weight="distance"),
                      "communities_largest_only": [sorted(c) for c in communities],
                      "modularity_not_p_value": q, "graphml_round_trip": "passed"}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Укажите каталог для новых синтетических файлов")
    run(sys.argv[1])
