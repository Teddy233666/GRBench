
SELECT load_labels_from_file('sciscinet_graph', 'Authors_Gender',
    'legacy_core/temp/grbench_update6_authors_gender_id_masked.csv');
SELECT load_edges_from_file('sciscinet_graph', 'Papers_to_Authors',
    'legacy_core/temp/grbench_update6_papers_to_authors_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'affiliated_with',
    'legacy_core/temp/grbench_update6_affiliated_with_with_types.csv');