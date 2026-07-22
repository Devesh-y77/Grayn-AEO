def chunked_in_fetch(db_client, table_name, select_cols, workspace_id, in_column, id_list, chunk_size=40, extra_filters=None):
    results = []
    if extra_filters is None:
        extra_filters = {}
    if not id_list:
        return results
        
    for i in range(0, len(id_list), chunk_size):
        chunk = id_list[i:i+chunk_size]
        q = db_client.table(table_name).select(select_cols).in_(in_column, chunk)
        if workspace_id:
            q = q.eq("workspace_id", str(workspace_id))
        for k, v in extra_filters.items():
            q = q.eq(k, v)
        res = q.execute()
        if hasattr(res, 'data') and res.data:
            results.extend(res.data)
    return results
