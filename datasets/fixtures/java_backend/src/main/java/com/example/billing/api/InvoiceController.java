package com.example.billing.api;

import com.example.billing.service.InvoiceService;

public class InvoiceController {
  private final InvoiceService service;

  public InvoiceController(InvoiceService service) {
    this.service = service;
  }

  public String listJson() {
    return service.listAsJson();
  }
}
