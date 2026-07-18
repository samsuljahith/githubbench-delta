package com.example.billing;

import com.example.billing.api.InvoiceController;
import com.example.billing.service.InvoiceService;

public class App {
  public static void main(String[] args) {
    InvoiceController controller = new InvoiceController(new InvoiceService());
    System.out.println(controller.listJson());
  }
}
