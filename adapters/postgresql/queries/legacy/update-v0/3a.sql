SELECT load_labels_from_file('sciscinet_graph', 'Papers',
    'legacy_core/temp/grbench_update1_papers_id_masked.csv');

SELECT load_edges_from_file('sciscinet_graph', 'Papers_to_Authors',
    'legacy_core/temp/grbench_update3_papers_to_authors_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'contributed_from',
    'legacy_core/temp/grbench_update3_contributed_from_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'PaperReferences',
    'legacy_core/temp/grbench_update3_paperreferences_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'Link_NSF',
    'legacy_core/temp/grbench_update3_link_nsf_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'Link_NIH',
    'legacy_core/temp/grbench_update3_link_nih_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'Link_ClinicalTrials',
    'legacy_core/temp/grbench_update3_link_clinicaltrials_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'link_newsfeed',
    'legacy_core/temp/grbench_update3_link_newsfeed_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'link_twitter',
    'legacy_core/temp/grbench_update3_link_twitter_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'PaperFields',
    'legacy_core/temp/grbench_update3_paperfields_with_types.csv');