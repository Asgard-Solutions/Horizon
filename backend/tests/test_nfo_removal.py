"""Recoverable NFO removal, exercised only against disposable media folders."""
from pathlib import Path
from types import SimpleNamespace
import os

import pytest

from mediacenter import nfo_document as nfo


@pytest.mark.skipif(os.name!='nt',reason='Windows file-handle sharing semantics')
def test_confirmed_file_is_held_against_external_replacement_until_archived(tmp_path,monkeypatch):
    path=tmp_path/'movie.nfo';path.write_bytes(b'confirmed original')
    replacement=tmp_path/'replacement.nfo';replacement.write_bytes(b'new unconfirmed file')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    rename=os.rename
    def interleave(source,destination,*args,**kwargs):
        os.replace(replacement,path)
        return rename(source,destination,*args,**kwargs)
    monkeypatch.setattr(os,'rename',interleave)
    rename_handle=nfo._win_archive_handle
    def while_handle_is_open(fd,destination):
        with pytest.raises(PermissionError):os.replace(replacement,path)
        return rename_handle(fd,destination)
    monkeypatch.setattr(nfo,'_win_archive_handle',while_handle_is_open)
    result=nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert Path(result['backup_path']).read_bytes()==b'confirmed original'
    assert replacement.read_bytes()==b'new unconfirmed file'


def test_remove_retains_exact_file_in_recovery_backup(tmp_path):
    path=tmp_path/'movie.nfo';content=b'<movie><title>Duplicate</title></movie>\nhttps://example.test/movie/1'
    path.write_bytes(content)
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    result=nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert not path.exists()
    assert Path(result['backup_path']).read_bytes()==content
    assert Path(result['backup_path']).parent==tmp_path
    assert result['backup_path'].endswith('.bak')


@pytest.mark.skipif(os.name!='nt',reason='Windows extended-length rename paths')
def test_recovery_path_can_exceed_legacy_windows_path_limit(tmp_path):
    parent=tmp_path/('nested-'+('x'*45));parent.mkdir()
    path=parent/'movie.nfo';path.write_bytes(b'long path recovery')
    assert len(str(path))+53>=260
    doc=nfo.inspect_document(str(path),[str(tmp_path)])
    result=nfo.remove_document(str(path),[str(tmp_path)],doc['revision'])
    assert Path(result['backup_path']).read_bytes()==b'long path recovery'


def test_removal_waits_for_scan_and_rejects_client_paths(host,library):
    from mediacenter.scanner import SCAN_LOCK
    item=host.get('/api/nfo/items?kind=movie&query=Sample Movie').json()['items'][0]
    endpoint=f"/api/nfo/document/movie/{item['id']}"
    doc=host.get(endpoint).json();payload={'revision':doc['revision'],'document_key':doc['document_key']}
    assert host.post(endpoint+'/delete',json={**payload,'path':'other.nfo'}).status_code==422
    with SCAN_LOCK:
        assert host.post(endpoint+'/delete',json=payload).status_code==409
    assert Path(doc['path']).exists()


@pytest.mark.parametrize('kind',['tv','episode'])
def test_show_and_episode_nfo_removal(host,library,media_root,kind):
    show=host.get('/api/nfo/items?kind=tv&query=Sample Show').json()['items'][0]
    if kind=='tv':item=show
    else:
        path=media_root/'TV'/'Sample Show'/'Season 01'/'Sample Show - S01E01.nfo'
        path.write_text('<episodedetails><title>Episode metadata</title></episodedetails>')
        item=host.get(f"/api/nfo/items?kind=episode&show_id={show['id']}").json()['items'][0]
    endpoint=f"/api/nfo/document/{kind}/{item['id']}"
    doc=host.get(endpoint).json();original=Path(doc['path']).read_bytes()
    result=host.post(endpoint+'/delete',json={'revision':doc['revision'],'document_key':doc['document_key']})
    assert result.status_code==200,result.text
    assert Path(result.json()['backup_path']).read_bytes()==original
    assert host.get(f"/api/shows/{show['id']}").status_code==200


def test_duplicate_nfo_cannot_be_removed_using_previous_file_identity(host,library,app):
    from mediacenter.db import connect
    item=host.get('/api/nfo/items?kind=movie&query=Sample Movie').json()['items'][0]
    endpoint=f"/api/nfo/document/movie/{item['id']}"
    doc=host.get(endpoint).json();old=Path(doc['path'])
    # The shared test folder contains multiple movies, so its folder-wide NFO
    # must not be treated as another title's sidecar. Use a dedicated source.
    conn=connect(app.state.config.db_path)
    name=conn.execute('SELECT filename FROM media_files WHERE id=(SELECT file_id FROM movies WHERE id=?)',(item['id'],)).fetchone()[0]
    dedicated=old.parent.parent.parent/'dedicated';dedicated.mkdir()
    (dedicated/name).write_bytes(b'owned duplicate verification')
    stem=dedicated/Path(name).with_suffix('.nfo').name
    stem.write_bytes(b'<movie><title>Two local NFOs</title></movie>')
    fallback=dedicated/'movie.nfo';fallback.write_bytes(b'<movie><title>Fallback local NFO</title></movie>')
    assert host.post('/api/libraries',json={'path':str(dedicated)}).status_code==200
    selected=host.get('/api/nfo/items?kind=movie&query=Two local NFOs').json()['items'][0]
    endpoint=f"/api/nfo/document/movie/{selected['id']}";doc=host.get(endpoint).json()
    payload={'revision':doc['revision'],'document_key':doc['document_key']}
    assert host.post(endpoint+'/delete',json=payload).status_code==200
    assert host.post(endpoint+'/delete',json=payload).status_code==409
    next_file=host.get(endpoint).json()
    assert next_file['path']==str(fallback) and next_file['fields']['title']=='Fallback local NFO'
    assert fallback.exists()
    conn.close()


def test_inspection_and_removal_allow_unsupported_xml_without_parsing(tmp_path):
    path=tmp_path/'movie.nfo';path.write_bytes(b'broken local metadata')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    assert document['size']==21
    result=nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert Path(result['backup_path']).read_bytes()==b'broken local metadata'


def test_stale_revision_keeps_current_file(tmp_path):
    path=tmp_path/'movie.nfo';path.write_bytes(b'original')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    path.write_bytes(b'changed externally')
    with pytest.raises(nfo.NfoError) as error:
        nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert error.value.status==409
    assert path.read_bytes()==b'changed externally'
    assert len(list(tmp_path.iterdir()))==1


def test_existing_recovery_is_not_overwritten(tmp_path,monkeypatch):
    path=tmp_path/'movie.nfo';path.write_bytes(b'original')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    monkeypatch.setattr(nfo.uuid,'uuid4',lambda:SimpleNamespace(hex='fixed'))
    backup=tmp_path/'movie.nfo.horizon-deleted-fixed.bak';backup.write_bytes(b'earlier recovery')
    with pytest.raises(nfo.NfoError):
        nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert backup.read_bytes()==b'earlier recovery'
    assert path.read_bytes()==b'original'


def test_rename_failure_keeps_original(tmp_path,monkeypatch):
    path=tmp_path/'movie.nfo';path.write_bytes(b'original')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    def fail(*args,**kwargs):raise PermissionError('no removal permission')
    monkeypatch.setattr(nfo._Guard,'archive',fail)
    with pytest.raises(nfo.NfoError):
        nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert path.read_bytes()==b'original'


def test_removal_reuses_path_and_hardlink_protection(tmp_path):
    path=tmp_path/'movie.nfo';path.write_bytes(b'original')
    document=nfo.inspect_document(str(path),[str(tmp_path)])
    with pytest.raises(nfo.NfoError):nfo.remove_document(str(path),[str(tmp_path/'other')],document['revision'])
    alias=tmp_path/'alias.nfo';alias.hardlink_to(path)
    with pytest.raises(nfo.NfoError):nfo.remove_document(str(path),[str(tmp_path)],document['revision'])
    assert path.read_bytes()==b'original'


def test_removal_route_authorization_revision_and_unchanged_catalog(host,library,app):
    from mediacenter.db import connect
    item=host.get('/api/nfo/items?kind=movie&query=Sample Movie').json()['items'][0]
    endpoint=f"/api/nfo/document/movie/{item['id']}"
    doc=host.get(endpoint).json();path=Path(doc['path']);content=path.read_bytes()
    conn=connect(app.state.config.db_path)
    counts={t:conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['media_files','movies','shows','episodes','progress']}
    response=host.post(endpoint+'/delete',json={'revision':doc['revision'],'document_key':doc['document_key']})
    assert response.status_code==200,response.text
    assert not path.exists() and Path(response.json()['backup_path']).read_bytes()==content
    assert host.get(endpoint).status_code==404
    assert host.get(f"/api/movies/{item['id']}").status_code==200
    assert counts=={t:conn.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in counts}
    conn.close()


def test_removal_invalid_xml_host_csrf_and_stale_key(host,library,lan_client_factory):
    item=host.get('/api/nfo/items?kind=movie&query=Sample Movie').json()['items'][0]
    endpoint=f"/api/nfo/document/movie/{item['id']}"
    doc=host.get(endpoint).json();path=Path(doc['path']);path.write_bytes(b'broken metadata')
    doc=host.get(endpoint).json()
    assert doc['fields'] is None and doc['read_error']
    payload={'revision':doc['revision'],'document_key':doc['document_key']}
    assert lan_client_factory().post(endpoint+'/delete',json=payload).status_code==403
    assert host.post(endpoint+'/delete',json=payload,headers={'X-MC-Client':''}).status_code==403
    assert host.post(endpoint+'/delete',json={**payload,'document_key':'0'*64}).status_code==409
    path.write_bytes(b'changed again')
    assert host.post(endpoint+'/delete',json=payload).status_code==409
    doc=host.get(endpoint).json()
    assert host.post(endpoint+'/delete',json={'revision':doc['revision'],'document_key':doc['document_key']}).status_code==200
