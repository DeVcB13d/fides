package devtools.validation

import devtools.App
import devtools.Generators._
import devtools.domain.enums.PolicyValueGrouping
import devtools.domain.enums.RuleInclusion.ALL
import devtools.domain.policy.PolicyRule
import devtools.domain.{DataSubjectCategory, SystemObject}
import devtools.util.waitFor
import org.scalatest.matchers.should.Matchers.convertToAnyShouldWrapper

class DataSubjectCategoryValidatorTest
  extends ValidatorTestBase[DataSubjectCategory, Long](
    DataSubjectCategoryGen,
    App.dataSubjectCategoryDAO,
    App.subjectCategoryValidator
  ) {

  private val sDao                          = App.systemDAO
  private val prDao                         = App.policyRuleDAO
  var newKey: String                        = ""
  var newKeyId: Long                        = 0
  var newTaxonomyValue: DataSubjectCategory = _
  var newSystem: SystemObject               = _
  var newPolicyRule: PolicyRule             = _
  var child: DataSubjectCategory            = _
  override def beforeAll(): Unit = {
    newKey = fidesKey
    newTaxonomyValue = waitFor(dao.create(DataSubjectCategory(0, None, 1, newKey, None, None)))
    newKeyId = newTaxonomyValue.id
    newSystem = waitFor(
      sDao.create(
        blankSystem.copy(declarations = Seq(DeclarationGen.sample.get.copy(dataSubjectCategories = Set(newKey))))
      )
    )

    newPolicyRule = waitFor(
      prDao.create(
        PolicyRuleGen.sample.get.copy(organizationId = 1, dataSubjectCategories = PolicyValueGrouping(ALL, Set(newKey)))
      )
    )
    createdIds.add(newKeyId)
    child = waitFor(dao.create(DataSubjectCategory(0, Some(newKeyId), 1, newKey + "child", None, None)))
    createdIds.add(child.id)
  }

  override def afterAll(): Unit = {
    super.afterAll()
    sDao.delete(newSystem.id)
  }

  test("create requires organization exists") {
    createValidationErrors(_.copy(organizationId = randomLong)) should containMatchString("organization")
  }

  test("create requires parent exists ") {
    createValidationErrors(_.copy(parentId = Some(randomLong))) should containMatchString("parent")
  }

  test("update requires parent exists if not null") {
    updateValidationErrors(
      gen.sample.get.copy(parentId = None),
      _.copy(parentId = Some(randomLong))
    ) should containMatchString("parentId")
  }

  test("update or delete with fides key in use by system fails") {
    //attempt to update with new key
    updateValidationErrors(
      DataSubjectCategory(newKeyId, None, 1, "tryingToChangeTheFidesKeyOfAnInUseValue", None, None),
      newTaxonomyValue
    ) should containMatchString("is in use in systems")
    //attempt to delete with the new key
    deleteValidationErrors(newKeyId) should containMatchString("is in use in systems")

    // test in policy rules
    updateValidationErrors(
      DataSubjectCategory(newKeyId, None, 1, "tryingToChangeTheFidesKeyOfAnInUseValue", None, None),
      newTaxonomyValue
    ) should containMatchString("is in use in policy rules")
    //attempt to delete with the new key
    deleteValidationErrors(newKeyId) should containMatchString("is in use in policy rules")

    //delete system, update and delete should pass
    waitFor(sDao.delete(newSystem.id))
    updateValidationErrors(
      DataSubjectCategory(newKeyId, None, 1, "tryingToChangeTheFidesKeyOfAnInUseValue", None, None),
      newTaxonomyValue
    ) shouldNot containMatchString("systems")

    deleteValidationErrors(newKeyId) shouldNot containMatchString("systems")

    //delete policyrule, update and delete should pass
    waitFor(prDao.delete(newPolicyRule.id))
    updateValidationErrors(
      DataSubjectCategory(newKeyId, None, 1, "tryingToChangeTheFidesKeyOfAnInUseValue", None, None),
      newTaxonomyValue
    ) shouldNot containMatchString("is in use in policy rules")
    //attempt to delete with the new key
    deleteValidationErrors(newKeyId) shouldNot containMatchString("is in use in policy rules")
  }

  test("delete with children") {
    deleteValidationErrors(newKeyId) should containMatchString("child")
  }
}
