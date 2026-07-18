package httpapi

import (
	"encoding/json"
	"net/http"

	"github.com/example/inventoryapi/internal/store"
)

func NewMux() *http.ServeMux {
	mux := http.NewServeMux()
	s := store.New()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/items", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		_ = json.NewEncoder(w).Encode(s.List())
	})
	return mux
}
