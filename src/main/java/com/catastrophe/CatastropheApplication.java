package com.catastrophe;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class CatastropheApplication {
  public static void main(String[] args) {
    SpringApplication.run(CatastropheApplication.class, args);
    System.out.println("🚀 Application démarrée sur http://localhost:8080");
    System.out.println("📊 Console H2 : http://localhost:8080/h2-console");
    System.out.println("   JDBC URL: jdbc:h2:file:./data/catastrophe_db");
    System.out.println("   User: sa, Password: (vide)");
  }
}
