from cStringIO import StringIO
from libmproxy import console, proxy, filt, flow
import utils
import libpry


class uServerPlaybackState(libpry.AutoTree):
    def test_hash(self):
        s = flow.ServerPlaybackState()
        r = utils.tflow()
        r2 = utils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

    def test_load(self):
        s = flow.ServerPlaybackState()
        r = utils.tflow()
        r.request.headers["key"] = ["one"]

        r2 = utils.tflow()
        r2.request.headers["key"] = ["two"]

        s.load([r, r2])
        assert len(s) == 2
        assert len(s.fmap.keys()) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["one"]
        assert len(s) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["two"]
        assert len(s) == 0

        assert not s.next_flow(r)


class uFlow(libpry.AutoTree):
    def test_run_script(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        se = f.run_script("scripts/a")
        assert "DEBUG" == se.strip()
        assert f.request.host == "TESTOK"

    def test_run_script_err(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        libpry.raises("returned error", f.run_script,"scripts/err_return")
        libpry.raises("invalid response", f.run_script,"scripts/err_data")
        libpry.raises("no such file", f.run_script,"nonexistent")
        libpry.raises("permission denied", f.run_script,"scripts/nonexecutable")

    def test_match(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        assert not f.match(filt.parse("~b test"))
        assert not f.match(None)

    def test_backup(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        f.request.content = "foo"
        assert not f.modified()
        f.backup()
        f.request.content = "bar"
        assert f.modified()
        f.revert()
        assert f.request.content == "foo"

    def test_getset_state(self):
        f = utils.tflow()
        f.response = utils.tresp(f.request)
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

        f.response = None
        f.error = proxy.Error(f.request, "error")
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

        f2 = utils.tflow()
        f2.error = proxy.Error(f.request, "e2")
        assert not f == f2
        f.load_state(f2.get_state())
        assert f == f2



    def test_kill(self):
        f = utils.tflow()
        f.request = utils.treq()
        f.intercept()
        assert not f.request.acked
        f.kill()
        assert f.request.acked
        f.intercept()
        f.response = utils.tresp()
        f.request = f.response.request
        f.request.ack()
        assert not f.response.acked
        f.kill()
        assert f.response.acked

    def test_accept_intercept(self):
        f = utils.tflow()
        f.request = utils.treq()
        f.intercept()
        assert not f.request.acked
        f.accept_intercept()
        assert f.request.acked
        f.response = utils.tresp()
        f.request = f.response.request
        f.intercept()
        f.request.ack()
        assert not f.response.acked
        f.accept_intercept()
        assert f.response.acked

    def test_serialization(self):
        f = flow.Flow(None)
        f.request = utils.treq()


class uState(libpry.AutoTree):
    def test_backup(self):
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        req = utils.treq()
        f = c.add_request(req)

        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        c.clientconnect(bc)
        assert len(c.client_connections) == 1

        req = utils.treq(bc)
        f = c.add_request(req)
        assert f
        assert len(c.flow_list) == 1
        assert c.flow_map.get(req)

        newreq = utils.treq()
        assert c.add_request(newreq)
        assert c.flow_map.get(newreq)

        resp = utils.tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 2
        assert c.flow_map.get(resp.request)

        newresp = utils.tresp()
        assert not c.add_response(newresp)
        assert not c.flow_map.get(newresp.request)

        dc = proxy.ClientDisconnect(bc)
        c.clientdisconnect(dc)
        assert not c.client_connections

    def test_err(self):
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        req = utils.treq()
        f = c.add_request(req)
        e = proxy.Error(f.request, "message")
        assert c.add_error(e)

        e = proxy.Error(utils.tflow().request, "message")
        assert not c.add_error(e)

    def test_view(self):
        c = flow.State()

        req = utils.treq()
        c.clientconnect(req.client_conn)
        assert len(c.view) == 0

        f = c.add_request(req)
        assert len(c.view) == 1

        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 0
        resp = utils.tresp(req)
        c.add_response(resp)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        req = utils.treq()
        c.clientconnect(req.client_conn)
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 1
        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 1

    def _add_request(self, state):
        req = utils.treq()
        f = state.add_request(req)
        return f

    def _add_response(self, state):
        req = utils.treq()
        f = state.add_request(req)
        resp = utils.tresp(req)
        state.add_response(resp)

    def _add_error(self, state):
        req = utils.treq()
        f = state.add_request(req)
        f.error = proxy.Error(f.request, "msg")

    def test_kill_flow(self):
        c = flow.State()
        req = utils.treq()
        f = c.add_request(req)
        c.kill_flow(f)
        assert not c.flow_list

    def test_clear(self):
        c = flow.State()
        f = self._add_request(c)
        f.intercepting = True

        c.clear()
        assert len(c.flow_list) == 1
        f.intercepting = False
        c.clear()
        assert len(c.flow_list) == 0

    def test_dump_flows(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_error(c)

        flows = c.view[:]
        c.clear()
        
        c.load_flows(flows)
        assert isinstance(c.flow_list[0], flow.Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all()


class uSerialize(libpry.AutoTree):
    def test_roundtrip(self):
        sio = StringIO()
        f = utils.tflow()
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1
        assert l[0] == f


class uFlowMaster(libpry.AutoTree):
    def test_all(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        req = utils.treq()

        fm.handle_clientconnect(req.client_conn)

        f = fm.handle_request(req)
        assert len(s.flow_list) == 1

        resp = utils.tresp(req)
        fm.handle_response(resp)
        assert len(s.flow_list) == 1

        rx = utils.tresp()
        assert not fm.handle_response(rx)
        
        dc = proxy.ClientDisconnect(req.client_conn)
        fm.handle_clientdisconnect(dc)

        err = proxy.Error(f.request, "msg")
        fm.handle_error(err)

    def test_replay(self):
        s = flow.State()

        f = utils.tflow()
        f.response = utils.tresp(f.request)
        pb = [f]

        fm = flow.FlowMaster(None, s)
        assert not fm.playback(utils.tflow())

        fm.start_playback(pb)
        assert fm.playback(utils.tflow())

        fm.start_playback(pb)
        r = utils.tflow()
        r.request.content = "gibble"
        assert not fm.playback(r)



tests = [
    uServerPlaybackState(),
    uFlow(),
    uState(),
    uSerialize(),
    uFlowMaster()

]