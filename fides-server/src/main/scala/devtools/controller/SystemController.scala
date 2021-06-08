package devtools.controller

import devtools.controller.definition.ApiResponse.asyncResponse
import devtools.controller.definition.{BaseController, GetByUniqueKey, LongPK}
import devtools.domain.{Approval, SystemObject}
import devtools.persist.dao.UserDAO
import devtools.persist.service.{PolicyService, SystemService}
import devtools.util.FidesYamlProtocols
import net.jcazevedo.moultingyaml.YamlFormat
import org.scalatra.swagger.Swagger

import scala.concurrent.{ExecutionContext, Future}
import scala.util.{Failure, Success}

class SystemController(
  val service: SystemService,
  val policyService: PolicyService,
  val userDAO: UserDAO,
  val swagger: Swagger
)(implicit
  executor: ExecutionContext
) extends BaseController[SystemObject, Long] with LongPK[SystemObject] with GetByUniqueKey[SystemObject] {

  val yamlFormat: YamlFormat[SystemObject] = FidesYamlProtocols.SystemObjectFormat

  /** Default input values that are part of system object but we don't expect as part of the post */

  override val inputMergeMap = Map("id" -> 0, "creationTime" -> null, "lastUpdateTime" -> null)

  post(
    "/validateForCreate",
    operation(
      apiOperation[SystemObject](s"validateForCreate system")
        .summary(s"validateForCreate (pre-flight) a system and report on any errors")
    )
  ) {
    asyncResponse {
      ingest(request.body, request.getHeader("Content-Type"), inputMergeMap) match {
        case Success(t)         => service.validator.validateForCreate(t, requestContext).map(_ => t)
        case Failure(exception) => Future.failed(exception)
      }
    }
  }

  post(
    "/dry-run",
    operation(
      apiOperation[Approval](s"rate system")
        .summary(s"submit a system for approval")
    )
  ) {
    asyncResponse {
      ingest(request.body, request.getHeader("Content-Type"), inputMergeMap) match {
        case Success(t)         => service.dryRun(t, requestContext)
        case Failure(exception) => Future.failed(exception)
      }
    }
  }

}
