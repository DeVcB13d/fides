describe("Connectors", () => {
  beforeEach(() => {
    cy.login();
  });
  describe("Configuring connectors", () => {
    beforeEach(() => {
      cy.intercept("GET", "/api/v1/connection*", {
        fixture: "connectors/list.json",
      }).as("getConnectors");
      cy.intercept("GET", "/api/v1/connection_type*", {
        fixture: "connectors/connection_types.json",
      }).as("getConnectionTypes");
      cy.intercept("GET", "/api/v1/connection/postgres_connector", {
        fixture: "connectors/postgres_connector.json",
      }).as("getPostgresConnector");
      cy.intercept("GET", "/api/v1/connection_type/postgres/secret", {
        fixture: "connectors/postgres_secret.json",
      }).as("getPostgresConnectorSecret");
      cy.intercept(
        "GET",
        "/api/v1/connection/postgres_connector/datasetconfig",
        {
          fixture: "connectors/datasetconfig.json",
        }
      ).as("getPostgresConnectorDatasetconfig");

      cy.intercept("POST", "/api/v1/dataset/upsert", { body: {} }).as(
        "upsertDataset"
      );
      cy.intercept(
        "PATCH",
        "/api/v1/connection/postgres_connector/datasetconfig",
        { body: {} }
      ).as("patchDatasetconfig");
      cy.intercept("GET", "/api/v1/dataset", { fixture: "datasets.json" }).as(
        "getDatasets"
      );
    });

    it("Should show data store connections and view configuration", () => {
      cy.visit("/datastore-connection");
      cy.getByTestId("connection-grid-item-mongodb_connector");
      cy.getByTestId("connection-grid-item-postgres_connector").within(() => {
        cy.getByTestId("connection-menu-btn").click();
      });
      cy.getByTestId("connection-menu-postgres_connector").within(() => {
        cy.getByTestId("configure-btn").click();
      });
      cy.getByTestId("input-name").should("have.value", "postgres_connector");
    });

    it("Should allow saving a dataset configuration via dropdown", () => {
      cy.visit("/datastore-connection/postgres_connector");
      cy.getByTestId("tab-Dataset configuration").click();
      cy.wait("@getPostgresConnectorDatasetconfig");

      // The yaml editor will start off disabled
      cy.getByTestId("save-yaml-btn").should("be.disabled");
      // The dataset dropdown selector should have the value of the existing connected dataset
      cy.getByTestId("save-dataset-link-btn").should("be.enabled");
      cy.getByTestId("dataset-selector").should(
        "have.value",
        "postgres_example_test_dataset"
      );

      // Change the linked dataset
      cy.getByTestId("dataset-selector").select("demo_users_dataset_2");
      cy.getByTestId("save-dataset-link-btn").click();

      cy.wait("@patchDatasetconfig").then((interception) => {
        expect(interception.request.body).to.eql([
          {
            fides_key: "postgres_example_test_dataset",
            ctl_dataset_fides_key: "demo_users_dataset_2",
          },
        ]);
      });
    });

    it("Should allow saving a dataset configuration via yaml", () => {
      cy.visit("/datastore-connection/postgres_connector");
      cy.getByTestId("tab-Dataset configuration").click();
      cy.wait("@getPostgresConnectorDatasetconfig");

      // Unset the linked dataset, which should switch the save button enable-ness
      cy.getByTestId("dataset-selector").select("Select");
      cy.getByTestId("save-dataset-link-btn").should("be.disabled");
      // The monaco yaml editor takes a bit to load
      // eslint-disable-next-line cypress/no-unnecessary-waiting
      cy.wait(1000);
      cy.getByTestId("save-yaml-btn").click();

      // Click past the confirmation modal
      cy.getByTestId("confirmation-modal");
      cy.getByTestId("continue-btn").click();

      cy.wait("@upsertDataset").then((interception) => {
        expect(interception.request.body.length).to.eql(1);
        expect(interception.request.body[0].fides_key).to.eql(
          "postgres_example_test_dataset"
        );
      });
      cy.wait("@patchDatasetconfig").then((interception) => {
        expect(interception.request.body).to.eql([
          {
            fides_key: "postgres_example_test_dataset",
            ctl_dataset_fides_key: "postgres_example_test_dataset",
          },
        ]);
      });
    });

    it("Should not show the dataset selector if no datasets exist", () => {
      cy.intercept("GET", "/api/v1/dataset", { body: [] }).as("getDatasets");
      cy.intercept(
        "GET",
        "/api/v1/connection/postgres_connector/datasetconfig",
        {
          body: {
            items: [],
          },
        }
      ).as("getEmptyPostgresConnectorDatasetconfig");

      cy.visit("/datastore-connection/postgres_connector");
      cy.getByTestId("tab-Dataset configuration").click();
      cy.wait("@getEmptyPostgresConnectorDatasetconfig");
      cy.getByTestId("dataset-selector-section").should("not.exist");
    });
  });
});
