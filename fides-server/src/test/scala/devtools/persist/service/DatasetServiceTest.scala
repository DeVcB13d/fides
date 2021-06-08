package devtools.persist.service

import com.typesafe.scalalogging.LazyLogging
import devtools.Generators.{DatasetFieldGen, DatasetGen, DatasetTableGen, requestContext}
import devtools.domain.enums.AuditAction.{CREATE, DELETE, UPDATE}
import devtools.domain.{Dataset, DatasetField, DatasetTable}
import devtools.persist.dao.AuditLogDAO
import devtools.util.waitFor
import devtools.{App, TestUtils}
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers.convertToAnyShouldWrapper

import scala.collection.mutable
import scala.concurrent.ExecutionContext
class DatasetServiceTest extends AnyFunSuite with BeforeAndAfterAll with LazyLogging with TestUtils {
  private val datasetService  = App.datasetService
  private val datasetTableDAO = App.datasetTableDAO
  private val datasetFieldDAO = App.datasetFieldDAO

  private val auditLogDAO: AuditLogDAO            = App.auditLogDAO
  implicit val executionContext: ExecutionContext = App.executionContext
  private val datasetIds: mutable.Set[Long]       = mutable.HashSet[Long]()

  override def afterAll(): Unit = {
    datasetIds.foreach(App.datasetDAO.delete)
  }

  def matchTable(dataset: Dataset, tableName: String, f: (DatasetTable, DatasetTable) => Boolean): Unit = {
    val table   = dataset.tables.flatMap(_.find(_.name == tableName)).get
    val dbValue = waitFor(datasetTableDAO.findById(table.id)).get
    f(table, dbValue) shouldEqual true
  }
  def matchField(
    dataset: Dataset,
    tableName: String,
    fieldName: String,
    f: (DatasetField, DatasetField) => Boolean
  ): Unit = {
    val table = dataset.tables.flatMap(_.find(_.name == tableName)).get
    val field = table.fields.flatMap(_.find(_.name == fieldName))
    field.map { fld =>
      val dbValue = waitFor(datasetFieldDAO.findById(fld.id)).get
      f(fld, dbValue) shouldEqual true
    }
  }

  test("test dataset composite insert") {

    val f1  = DatasetFieldGen.sample.get.copy(creationTime = None, lastUpdateTime = None, name = "f1")
    val f21 = DatasetFieldGen.sample.get.copy(creationTime = None, lastUpdateTime = None, name = "f2.1")
    val f22 = DatasetFieldGen.sample.get.copy(creationTime = None, lastUpdateTime = None, name = "f2.2")
    val f3  = DatasetFieldGen.sample.get.copy(creationTime = None, lastUpdateTime = None, name = "f3")
    val f5  = DatasetFieldGen.sample.get.copy(creationTime = None, lastUpdateTime = None, name = "f5")
    val t1 = DatasetTableGen.sample.get
      .copy(
        creationTime = None,
        lastUpdateTime = None,
        name = "1",
        fields = Some(Seq(f1))
      )
    val t2 = DatasetTableGen.sample.get
      .copy(
        creationTime = None,
        lastUpdateTime = None,
        name = "2",
        fields = Some(Seq(f21, f22))
      )
    val t3 = DatasetTableGen.sample.get
      .copy(
        creationTime = None,
        lastUpdateTime = None,
        name = "3",
        fields = Some(Seq(f3))
      )
    val t4 = DatasetTableGen.sample.get
      .copy(creationTime = None, lastUpdateTime = None, name = "4", fields = Some(Seq()))
    val t5 = DatasetTableGen.sample.get
      .copy(creationTime = None, lastUpdateTime = None, name = "5", fields = Some(Seq()))
    val ds =
      DatasetGen.sample.get.copy(
        creationTime = None,
        lastUpdateTime = None,
        tables = Some(Seq(t1, t2, t3, t4))
      )

    //create a dataset with tables t1<f1, t2<{f2, f22}, t3<f3, t4<()
    val response = waitFor(datasetService.create(ds, requestContext))

    matchTable(response, t1.name, (a, b) => a.description == b.description)
    matchTable(response, t1.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)
    matchTable(response, t2.name, (a, b) => a.description == b.description)
    matchTable(response, t2.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)
    matchTable(response, t3.name, (a, b) => a.description == b.description)
    matchTable(response, t3.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)

    // response t1 has fields f1     // response t2 has fields f2, f3 // validate in dao
    matchField(response, t1.name, f1.name, (a, b) => a.description == b.description)
    matchField(response, t2.name, f21.name, (a, b) => a.description == b.description)
    matchField(response, t2.name, f22.name, (a, b) => a.description == b.description)
    matchField(response, t3.name, f3.name, (a, b) => a.description == b.description)

    waitFor(auditLogDAO.find(response.id, "Dataset", CREATE)).size shouldEqual 1

    datasetIds.add(response.id)

    //update a dataset with tables t1<f1(edit), t2<{f2, f22}(unchanged), t3 (omitted) , t4 <f5, t5(new)
    val updateValue = response.copy(
      tables = Some(
        Seq(
          t1.copy(fields =
            Some(Seq(f1.copy(name = "altered_" + f1.name)))
          ),  //change the name in an internal field value
          t2, //unchanged
          //t3 is omitted
          t4.copy(fields = Some(Seq(f5))),
          t5 //new table
        )
      )
    )

    val updatedResponse = waitFor(
      datasetService
        .update(updateValue, requestContext)
        .flatMap(_ => datasetService.findById(response.id, requestContext))
    ).get

    //response has tables t1, t2, t3
    matchTable(updatedResponse, t1.name, (a, b) => a.description == b.description)
    matchTable(updatedResponse, t1.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)
    matchTable(updatedResponse, t1.name, (_, b) => b.lastUpdateTime.nonEmpty)

    matchTable(updatedResponse, t2.name, (a, b) => a.description == b.description)
    matchTable(updatedResponse, t2.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)

    matchTable(updatedResponse, t4.name, (a, b) => a.description == b.description)
    matchTable(updatedResponse, t4.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)

    matchTable(updatedResponse, t5.name, (a, b) => a.description == b.description)
    matchTable(updatedResponse, t5.name, (_, b) => b.creationTime.nonEmpty && b.creationTime == b.lastUpdateTime)

    val t3_id = response.tables.get.find(_.name == t3.name).get.id
    waitFor(datasetTableDAO.findById(t3_id)) shouldEqual None

    // response t1 has fields f1     // response t2 has fields f2, f3 // validate in dao
    matchField(updatedResponse, t1.name, "altered_" + f1.name, (a, b) => a.name == b.name)
    matchField(updatedResponse, t2.name, f21.name, (a, b) => a.description == b.description)
    matchField(updatedResponse, t2.name, f21.name, (_, b) => b.creationTime == b.lastUpdateTime)
    matchField(updatedResponse, t4.name, f5.name, (a, b) => a.description == b.description)

    // we should have 1 update record in the audit log
    waitFor(auditLogDAO.find(response.id, "Dataset", UPDATE)).size shouldEqual 1

    //delete should increment the org version
    waitFor(datasetService.delete(response.id, requestContext))
    // we should have 1 delete record in the audit log
    waitFor(auditLogDAO.find(response.id, "Dataset", DELETE)).size shouldEqual 1

  }

}
