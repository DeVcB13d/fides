package devtools.domain

import devtools.domain.definition.{CanBeTree, WithFidesKey, IdType, OrganizationId, TreeItem}
import devtools.util.Sanitization.sanitizeUniqueIdentifier

import scala.collection.mutable

final case class DataUse(
  id: Long,
  parentId: Option[Long],
  organizationId: Long,
  fidesKey: String,
  name: Option[String],
  clause: Option[String],
  description: Option[String]
) extends WithFidesKey[DataUse, Long] with CanBeTree[Long, DataUseTree] with OrganizationId {
  override def withId(idValue: Long): DataUse = this.copy(id = idValue)

  def toTreeItem: DataUseTree =
    DataUseTree(
      id,
      parentId,
      fidesKey,
      name,
      clause.getOrElse(""),
      mutable.TreeSet[DataUseTree]()(Ordering.by[DataUseTree, Long](_.id))
    )
}
object DataUse {
  type Tupled = (Long, Option[Long], Long, String, Option[String], Option[String], Option[String])
  def toInsertable(s: DataUse): Option[Tupled] =
    Some(s.id, s.parentId, s.organizationId, sanitizeUniqueIdentifier(s.fidesKey), s.name, s.clause, s.description)

  def fromInsertable(t: Tupled): DataUse = DataUse(t._1, t._2, t._3, t._4, t._5, t._6, t._7)

}

final case class DataUseTree(
  id: Long,
  parentId: Option[Long],
  fidesKey: String,
  name: Option[String],
  clause: String,
  children: mutable.Set[DataUseTree]
) extends TreeItem[DataUseTree, Long] {}
