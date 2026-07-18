package store

type Item struct {
	SKU  string `json:"sku"`
	Name string `json:"name"`
}

type Store struct {
	items []Item
}

func New() *Store {
	return &Store{items: []Item{{SKU: "A1", Name: "Bolt"}}}
}

func (s *Store) List() []Item { return s.items }

func (s *Store) DeadDebug() string { return "debug" }
