import pytest
from unittest.mock import patch, MagicMock
from jptrain import api

# Sample HTML snippets
SAMPLE_MAIN_HTML = """
<html>
<body>
  <div class="mdAreaList">
    <a href="/diainfo/area/2">北海道</a>
    <a href="/diainfo/area/4">関東</a>
    <a href="/diainfo/area/6">近畿</a>
  </div>
</body>
</html>
"""

SAMPLE_AREA_HTML = """
<html>
<body>
  <span class="subText">6月6日 11時2分更新</span>
  <h2>現在運行情報のある<!-- -->路線</h2>
  <div class="elmTblLstLine trouble">
    <table>
      <tbody>
        <tr><th>路線</th><th>状況</th><th>詳細</th></tr>
        <tr>
          <td><a href="/diainfo/148/0">江ノ島電鉄線</a></td>
          <td><span class="icnAlert"></span><span class="colTrouble">列車遅延</span></td>
          <td>石上駅でのドア点検の影響で、列車...</td>
        </tr>
      </tbody>
    </table>
  </div>
  
  <h3>JR東日本</h3>
  <div class="elmTblLstLine">
    <table>
      <tbody>
        <tr><th>路線</th><th>状況</th><th>詳細</th></tr>
        <tr>
          <td><a href="/diainfo/21/0">山手線</a></td>
          <td>平常運転</td>
          <td>事故・遅延情報はありません</td>
        </tr>
        <tr>
          <td><a href="/diainfo/29/0">橫須賀線</a></td>
          <td><span class="colTrouble">運転計画</span></td>
          <td>保守工事の影響で、終日...</td>
        </tr>
      </tbody>
    </table>
  </div>
</body>
</html>
"""

SAMPLE_DETAIL_HTML = """
<html>
<body>
  <div id="mdServiceStatus">
    <dl>
      <dt><span class="icnAlertLarge"></span>列車遅延</dt>
      <dd class="trouble">
        <p>石上駅でのドア点検の影響で、列車に遅れが出ています。<span>（6月6日 10時45分掲載）</span></p>
      </dd>
    </dl>
  </div>
</body>
</html>
"""

@patch("jptrain.api.requests.get")
def test_get_areas(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_MAIN_HTML
    mock_get.return_value = mock_resp
    
    areas = api.get_areas()
    assert len(areas) >= 3
    # Check Kanto code
    kanto = next(a for a in areas if a["name"] == "関東")
    assert kanto["code"] == "4"
    assert kanto["english"] == "Kanto"

@patch("jptrain.api.requests.get")
def test_get_area_status(mock_get):
    def side_effect(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "area" in url:
            resp.text = SAMPLE_AREA_HTML
        else:
            resp.text = SAMPLE_DETAIL_HTML
        return resp
    mock_get.side_effect = side_effect
    
    res = api.get_area_status("4")
    assert isinstance(res, dict)
    assert res["update_time"] == "6月6日 11時2分更新"
    
    routes = res["routes"]
    # Should exclude the trouble summary at the top and include JR東日本
    assert len(routes) == 2
    
    yamanote = next(r for r in routes if r["route"] == "山手線")
    assert yamanote["operator"] == "JR東日本"
    assert yamanote["status"] == "平常運転"
    assert yamanote["detail"] == "事故・遅延情報はありません"
    assert yamanote["detail_url"] == "/diainfo/21/0"
    
    yokosuka = next(r for r in routes if r["route"] == "橫須賀線")
    assert yokosuka["operator"] == "JR東日本"
    assert yokosuka["status"] == "運転計画"
    assert yokosuka["detail"] == "石上駅でのドア点検の影響で、列車に遅れが出ています。"
    assert yokosuka["detail_url"] == "/diainfo/29/0"

@patch("jptrain.api.requests.get")
def test_get_route_detail(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_DETAIL_HTML
    mock_get.return_value = mock_resp
    
    detail = api.get_route_detail("/diainfo/148/0")
    assert detail["status"] == "列車遅延"
    assert detail["description"] == "石上駅でのドア点検の影響で、列車に遅れが出ています。"
    assert detail["update_time"] == "6月6日 10時45分掲載"

SAMPLE_ROUTE_HTML = """
<html>
<body>
  <div id="route01">
    <h2 class="title">ルート 1</h2>
    <ul class="priority"><li>早</li><li>楽</li></ul>
    <ul class="summary">
      <li class="time">10:28発→10:42着 14分</li>
      <li class="transfer">乗換：0回</li>
      <li class="fare">IC優先：253円</li>
      <li class="distance">10.3km</li>
    </ul>
    <div class="routeDetail">
      <div class="station">
        <ul class="time"><li>10:28</li></ul>
        <p class="icon"><span class="icnStaDep">発</span></p>
        <dl><dt>東京</dt></dl>
      </div>
      <div class="fareSection">
        <div class="access trouble">
          <ul class="info">
            <li class="transport">
              <div>ＪＲ中央線快速<span class="destination">豊田行</span></div>
            </li>
            <li class="serviceStatus">
              <a href="/diainfo/123/0">列車遅延</a>
            </li>
          </ul>
        </div>
      </div>
      <div class="station">
        <ul class="time"><li>10:42</li></ul>
        <p class="icon"><span class="icnStaArr">着</span></p>
        <dl><dt>新宿</dt></dl>
      </div>
    </div>
  </div>
</body>
</html>
"""

SAMPLE_ROUTE_ERROR_HTML = """
<html>
<body>
  <script id="__NEXT_DATA__" type="application/json">
  {
    "props": {
      "pageProps": {
        "queryState": {
          "errorList": ["「invalid_station」に該当する出発地はありませんでした。"]
        }
      }
    }
  }
  </script>
</body>
</html>
"""

@patch("jptrain.api.requests.get")
def test_get_route_search_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_ROUTE_HTML
    mock_get.return_value = mock_resp
    
    res = api.get_route_search("東京", "新宿")
    assert not res["errors"]
    assert len(res["routes"]) == 1
    
    r = res["routes"][0]
    assert r["title"] == "ルート 1"
    assert r["priorities"] == ["早", "楽"]
    assert "10:28" in r["time"]
    assert "0" in r["transfer"]
    assert "253" in r["fare"]
    assert "10.3km" in r["distance"]
    
    segments = r["segments"]
    assert len(segments) == 3
    assert segments[0]["type"] == "station"
    assert segments[0]["name"] == "東京"
    assert segments[0]["status"] == "発"
    
    assert segments[1]["type"] == "transport"
    assert segments[1]["name"] == "ＪＲ中央線快速"
    assert segments[1]["destination"] == "豊田行"
    assert segments[1]["status"] == "列車遅延"
    assert segments[1]["detail_url"] == "/diainfo/123/0"
    
    assert segments[2]["type"] == "station"
    assert segments[2]["name"] == "新宿"
    assert segments[2]["status"] == "着"

@patch("jptrain.api.requests.get")
def test_get_route_search_error(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_ROUTE_ERROR_HTML
    mock_get.return_value = mock_resp
    
    res = api.get_route_search("invalid_station", "東京")
    assert len(res["errors"]) == 1
    assert "該当する出発地はありませんでした" in res["errors"][0]
    assert len(res["routes"]) == 0

