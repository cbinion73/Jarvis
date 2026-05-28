import CarPlay
import JarvisKit

/// Entry point for the JARVIS CarPlay UI.
///
/// iOS instantiates this delegate when the user connects to a CarPlay head unit.
/// We immediately hand off to `JarvisCarPlayController` which owns all template management.
final class CarPlaySceneDelegate: NSObject, CPTemplateApplicationSceneDelegate {

    private var controller: JarvisCarPlayController?

    // MARK: - CPTemplateApplicationSceneDelegate

    func templateApplicationScene(
        _ templateApplicationScene: CPTemplateApplicationScene,
        didConnect interfaceController: CPInterfaceController
    ) {
        let ctrl = JarvisCarPlayController(interfaceController: interfaceController)
        self.controller = ctrl
        ctrl.start()
    }

    func templateApplicationScene(
        _ templateApplicationScene: CPTemplateApplicationScene,
        didDisconnectInterfaceController interfaceController: CPInterfaceController
    ) {
        controller?.stop()
        controller = nil
    }
}
