//go:build testing

package hub

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"

	"github.com/pocketbase/pocketbase/core"
	"github.com/stretchr/testify/require"
	"golang.org/x/crypto/ssh"
)

// TestCreatorSignalQualifiedBinary connects the exact compiled release binary
// to a real temporary Hub WebSocket endpoint and requires a persisted up state.
func TestCreatorSignalQualifiedBinary(t *testing.T) {
	binary := os.Getenv("CREATOR_SIGNAL_QUALIFIED_AGENT_BINARY")
	if binary == "" {
		t.Skip("set CREATOR_SIGNAL_QUALIFIED_AGENT_BINARY to qualify a built agent")
	}
	if _, err := os.Stat(binary); err != nil {
		t.Fatal(err)
	}
	hub, app, err := createTestHub(t)
	require.NoError(t, err)
	defer cleanupTestHub(hub, app)
	signer, err := hub.GetSSHKey("")
	require.NoError(t, err)
	key := signer.PublicKey()
	user, err := createTestUser(app)
	require.NoError(t, err)
	system, err := createTestRecord(app, "systems", map[string]any{"name": "qualified-binary", "host": "127.0.0.1", "port": "45876", "status": "pending", "users": []string{user.Id}})
	require.NoError(t, err)
	_, err = createTestRecord(app, "fingerprints", map[string]any{"system": system.Id, "token": "qualified-token", "fingerprint": ""})
	require.NoError(t, err)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/beszel/agent-connect" {
			(&agentConnectRequest{hub: hub, req: r, res: w}).agentConnect()
			return
		}
		http.NotFound(w, r)
	}))
	defer server.Close()
	data := t.TempDir()
	cmd := exec.Command(binary, "--key", string(ssh.MarshalAuthorizedKey(key)), "--url", server.URL, "--token", "qualified-token", "--listen", "127.0.0.1:45876")
	cmd.Env = append(os.Environ(), "BESZEL_AGENT_DATA_DIR="+filepath.Join(data, "agent"), "BESZEL_AGENT_DISABLE_SSH=true")
	require.NoError(t, cmd.Start())
	defer func() { _ = cmd.Process.Kill(); _, _ = cmd.Process.Wait() }()
	deadline := time.Now().Add(5 * time.Second)
	for time.Now().Before(deadline) {
		record, findErr := app.FindRecordById("systems", system.Id)
		require.NoError(t, findErr)
		if record.GetString("status") == "up" {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatal(fmt.Errorf("qualified binary did not complete Hub WebSocket handshake and metrics registration"))
}
