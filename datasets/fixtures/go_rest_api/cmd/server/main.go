package main

import (
	"log"
	"net/http"

	"github.com/example/inventoryapi/internal/httpapi"
)

func main() {
	mux := httpapi.NewMux()
	log.Fatal(http.ListenAndServe(":8080", mux))
}
