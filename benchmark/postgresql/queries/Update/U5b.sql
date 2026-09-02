SELECT load_labels_from_file('sciscinet_graph', 'Papers',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update1_papers_id_masked.csv');

SELECT load_edges_from_file('sciscinet_graph', 'Papers_to_Authors',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_papers_to_authors_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'contributed_from',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_contributed_from_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'PaperReferences',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_paperreferences_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'Link_NSF',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_link_nsf_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'Link_NIH',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_link_nih_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'Link_ClinicalTrials',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_link_clinicaltrials_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'link_newsfeed',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_link_newsfeed_with_types.csv');
SELECT load_edges_from_file('sciscinet_graph', 'link_twitter',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_link_twitter_with_types.csv');

SELECT load_edges_from_file('sciscinet_graph', 'PaperFields',
    '{{UPDATE_PREPARED_ROOT}}/grbench_update3_paperfields_with_types.csv');
