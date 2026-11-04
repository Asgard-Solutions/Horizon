import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from mediacenter.db import connect


def test_local_nfo_selection_is_host_only(host, library, lan_client_factory):
    response = host.get('/api/nfo/items?kind=movie')
    assert response.status_code == 200
    assert response.json()['total'] == 3
    assert lan_client_factory().get('/api/nfo/items?kind=movie').status_code == 403


def select(host, kind='movie', title='Sample Movie'):
    items = host.get(f'/api/nfo/items?kind={kind}&query={title}').json()['items']
    assert items
    value = host.get(f"/api/nfo/document/{kind}/{items[0]['id']}")
    assert value.status_code == 200, value.text
    return items[0], value.json()


def save(host, item, document, **updates):
    return host.post(f"/api/nfo/document/{item['kind']}/{item['id']}", json={
        'revision':document['revision'], 'document_key':document['document_key'], 'fields':{**document['fields'],**updates}})


def test_movie_save_updates_existing_nfo_catalog_and_keeps_progress_and_media(host, app, library, media_root):
    item, doc = select(host)
    path = Path(doc['path']); before = path.read_bytes()
    media = path.with_suffix('.mp4'); media_hash = hashlib.sha256(media.read_bytes()).hexdigest()
    conn = connect(app.state.config.db_path)
    file = conn.execute('SELECT f.path_key FROM movies m JOIN media_files f ON f.id=m.file_id WHERE m.id=?', (item['id'],)).fetchone()
    conn.execute('INSERT INTO progress VALUES(?,?,?,?,?)',(file[0],50,200,0,'test'));conn.commit()
    result = save(host,item,doc,title='Corrected local title',sort_title='ZZZ sort override',tagline='Local tagline',plot='Edited local plot',genres=['Drama'],cast=[{'name':'Local actor','role':'Lead'}],set='Local collection')
    assert result.status_code == 200, result.text
    assert Path(result.json()['backup_path']).read_bytes() == before
    assert ET.parse(path).getroot().findtext('title') == 'Corrected local title'
    movie = host.get(f"/api/movies/{item['id']}").json()
    assert movie['title'] == 'Corrected local title' and movie['plot'] == 'Edited local plot'
    assert movie['cast'] == [{'name':'Local actor','role':'Lead'}]
    assert movie['tagline'] == 'Local tagline'
    assert conn.execute('SELECT sort_title FROM movies WHERE id=?',(item['id'],)).fetchone()[0] == 'zzz sort override'
    assert conn.execute('SELECT position FROM progress').fetchone()[0] == 50
    assert hashlib.sha256(media.read_bytes()).hexdigest() == media_hash
    assert host.post(f"/api/libraries/{library['id']}/scan").status_code == 200
    assert host.get(f"/api/movies/{item['id']}").json()['title'] == 'Corrected local title'
    assert conn.execute('SELECT COUNT(*) FROM movies').fetchone()[0] == 3
    conn.close()


def test_tv_show_and_episode_edit_existing_files_without_changing_order(host, app, library, media_root):
    item, doc = select(host,'tv','Sample Show')
    assert save(host,item,doc,title='Local show correction',plot='Show edited plot').status_code == 200
    show = host.get(f"/api/shows/{item['id']}").json()
    assert show['title'] == 'Local show correction'
    episodes = host.get(f"/api/nfo/items?kind=episode&show_id={item['id']}").json()['items']
    episode = episodes[0]
    original = host.get(f"/api/nfo/document/episode/{episode['id']}")
    assert original.status_code == 404
    path = media_root / 'TV' / 'Sample Show' / 'Season 01' / 'Sample Show - S01E01.nfo'
    path.write_text('<episodedetails><title>Existing episode</title><season>1</season><episode>1</episode><custom>keep</custom></episodedetails>')
    doc = host.get(f"/api/nfo/document/episode/{episode['id']}").json()
    assert save(host,episode,doc,title='Episode correction',plot='Edited episode plot').status_code == 200
    root=ET.parse(path).getroot()
    assert root.findtext('custom')=='keep' and root.findtext('episode')=='1' and root.findtext('season')=='1'
    refreshed=host.get(f"/api/shows/{item['id']}").json()['seasons'][0]['episodes'][0]
    assert refreshed['title']=='Episode correction' and refreshed['episode_number']==1


def test_external_change_and_stale_catalog_key_refuse_save(host, app, library):
    item,doc=select(host)
    path=Path(doc['path']);path.write_text('<movie><title>Changed by another application</title></movie>')
    assert save(host,item,doc,title='Stale edit').status_code==409
    assert ET.parse(path).getroot().findtext('title')=='Changed by another application'
    doc=host.get(f"/api/nfo/document/movie/{item['id']}").json()
    doc['document_key']='0'*64
    assert save(host,item,doc,title='Wrong entry').status_code==409


def test_validation_host_csrf_missing_and_removed_online_endpoints(host, library, lan_client_factory):
    assert host.get('/api/scraper/status').status_code==404
    assert host.post('/api/scraper/run',json={}).status_code==404
    item,doc=select(host)
    assert save(host,item,doc,title='').status_code==422
    remote=lan_client_factory()
    assert remote.get(f"/api/nfo/document/movie/{item['id']}").status_code==403
    assert save(remote,item,doc,title='Remote edit').status_code==403
    response=host.post(f"/api/nfo/document/movie/{item['id']}",headers={'X-MC-Client':''},json={})
    assert response.status_code==403
    missing=host.get('/api/nfo/items?kind=movie&query=Another').json()['items'][0]
    assert host.get(f"/api/nfo/document/movie/{missing['id']}").status_code==404
    assert host.get('/api/nfo/document/movie/999999').status_code==404


def test_flat_episode_source_retains_dedicated_show_metadata(host,app,library,tmp_path):
    flat=tmp_path/'flat';flat.mkdir();(flat/'Sample.Show.S03E01.mp4').write_bytes(b'owned')
    assert host.post('/api/libraries',json={'path':str(flat)}).status_code==200
    conn=connect(app.state.config.db_path)
    row=conn.execute("SELECT plot,poster_path FROM shows WHERE title='Sample Show'").fetchone()
    assert row['plot']=='Show plot' and row['poster_path']
    conn.close()


def test_large_nfo_and_legacy_fields_stay_consistent_after_save(host,library):
    item,doc=select(host)
    path=Path(doc['path'])
    content='<movie><title>Large NFO title</title><plot>Large NFO plot</plot><ratings><rating name="local" default="true" max="100"><value>85</value><votes>20</votes></rating></ratings><imdbid>tt1234567</imdbid><releasedate>2024-02-03</releasedate><custom>'+('x'*1005000)+'</custom></movie>'
    path.write_text(content)
    doc=host.get(f"/api/nfo/document/movie/{item['id']}").json()
    assert doc['fields']['rating']==8.5 and doc['fields']['premiered']=='2024-02-03'
    result=save(host,item,doc,title='Large corrected title')
    assert result.status_code==200,result.text
    movie=host.get(f"/api/movies/{item['id']}").json()
    assert movie['title']=='Large corrected title' and movie['plot']=='Large NFO plot'
    assert movie['rating']==8.5 and movie['premiered']=='2024-02-03'
    assert movie['external_ids']['imdb']=='tt1234567'


def test_combination_nfo_retains_trailing_links_and_refreshes_local_catalog(host,library):
    item,doc=select(host)
    path=Path(doc['path'])
    trailer=b'\r\nhttps://www.themoviedb.org/movie/123\r\nhttps://www.imdb.com/title/tt1234567'
    original=b'<?xml version="1.0" encoding="utf-8"?><movie><title>Combined local title</title><plot>Combined plot</plot><custom>Keep this tag</custom></movie>'+trailer
    path.write_bytes(original)
    response=host.get(f"/api/nfo/document/movie/{item['id']}")
    assert response.status_code==200,response.text
    doc=response.json()
    assert doc['fields']['title']=='Combined local title'
    result=save(host,item,doc,plot='Corrected combined plot')
    assert result.status_code==200,result.text
    assert path.read_bytes().endswith(trailer)
    assert b'<custom>Keep this tag</custom>' in path.read_bytes()
    assert Path(result.json()['backup_path']).read_bytes()==original
    assert host.get(f"/api/movies/{item['id']}").json()['plot']=='Corrected combined plot'
    assert host.post(f"/api/libraries/{library['id']}/scan").status_code==200
    assert host.get(f"/api/movies/{item['id']}").json()['title']=='Combined local title'
