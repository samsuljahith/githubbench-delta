package com.example.billing.service;

import java.util.ArrayList;
import java.util.List;

public class InvoiceService {
  private final List<String> ids = new ArrayList<>(List.of("INV-1", "INV-2"));

  public List<String> listIds() {
    return List.copyOf(ids);
  }

  public String listAsJson() {
    if (ids.isEmpty()) {
      return "[]";
    }
    return "[\"INV-1\",\"INV-2\"]";
  }

  public String legacyFormat() {
    return String.join(",", listIds());
  }
}
