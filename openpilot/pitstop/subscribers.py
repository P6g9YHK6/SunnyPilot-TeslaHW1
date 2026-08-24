import logging
import time

from cereal import messaging, log

logger = logging.getLogger("pitstop")


class SubscriberMixin:

  def _subscriber_loop(self, topic, attr, field):
    logger.info(f"[LOOP] {topic} subscriber started")
    try:
      sock = messaging.sub_sock(topic, conflate=True, timeout=1000)
      while self._running:
        msg = messaging.recv_one(sock)
        if msg is not None:
          setattr(self, attr, getattr(msg, field))
    except Exception:
      logger.warning(f"{topic} subscriber not available")
    logger.info(f"[LOOP] {topic} subscriber stopped")

  def _model_manager_loop(self):
    self._subscriber_loop('modelManagerSP', '_model_state', 'modelManagerSP')

  def _device_state_loop(self):
    self._subscriber_loop('deviceState', '_device_state', 'deviceState')

  def _gps_location_loop(self):
    self._subscriber_loop('gpsLocationExternal', '_gps_location', 'gpsLocationExternal')

  def _diag_loop(self):
    logger.info("[LOOP] diagnostic monitor started")
    try:
      sm = messaging.SubMaster([
        'liveCalibration', 'livePose', 'liveParameters', 'longitudinalPlan',
        'modelV2', 'cameraOdometry', 'driverMonitoringState',
        'liveTorqueParameters', 'radarState', 'liveDelay',
        'selfdriveState', 'managerState', 'controlsState',
        'longitudinalPlanSP', 'liveMapDataSP', 'carStateSP', 'selfdriveStateSP',
      ])
      while self._running:
        sm.update(2000)
        services = []
        for s in ['liveCalibration', 'livePose', 'liveParameters', 'longitudinalPlan',
                   'modelV2', 'cameraOdometry', 'driverMonitoringState',
                   'liveTorqueParameters', 'radarState', 'liveDelay']:
          readers = self._msgq_readers(s)
          services.append({
            'name': s, 'valid': bool(sm.valid[s]), 'alive': bool(sm.alive[s]),
            'freq_ok': bool(sm.freq_ok[s]), 'readers': readers,
          })
        sd = sm['selfdriveState']
        alert = {
          'text1': str(sd.alertText1), 'text2': str(sd.alertText2),
          'status': str(sd.alertStatus).split('.')[-1], 'type': str(sd.alertType),
        } if sm.seen['selfdriveState'] else None
        self._is_engaged = bool(sd.enabled) if sm.seen['selfdriveState'] else False
        processes = []
        if sm.seen['managerState']:
          for p in sm['managerState'].processes:
            processes.append({
              'name': str(p.name), 'running': bool(p.running), 'should_run': bool(p.shouldBeRunning),
            })
        self._diag = {
          'services': services,
          'services_ok': all(s['valid'] and s['alive'] and s['freq_ok'] for s in services),
          'alert': alert, 'processes': processes,
        }
        if sm.updated['liveCalibration']:
          lc = sm['liveCalibration']
          self._calibration = {
            'status': str(lc.calStatus).split('.')[-1], 'percent': lc.calPerc,
            'valid_blocks': lc.validBlocks,
            'pitch': lc.rpyCalib[0] if len(lc.rpyCalib) > 0 else None,
            'roll': lc.rpyCalib[1] if len(lc.rpyCalib) > 1 else None,
            'yaw': lc.rpyCalib[2] if len(lc.rpyCalib) > 2 else None,
          }
        try:
          lp = sm['liveParameters'] if sm.seen['liveParameters'] else None
          pose = sm['livePose'] if sm.seen['livePose'] else None
          ltp = sm['liveTorqueParameters'] if sm.seen['liveTorqueParameters'] else None
          ld = sm['liveDelay'] if sm.seen['liveDelay'] else None
          dms = sm['driverMonitoringState'] if sm.seen['driverMonitoringState'] else None
          sd2 = sm['selfdriveState'] if sm.seen['selfdriveState'] else None
          cs = sm['controlsState'].deprecated if sm.seen['controlsState'] else None
          self._cockpit_data = {
            "liveParameters": {
              "angleOffsetDeg": lp.angleOffsetDeg if lp is not None else None,
              "stiffnessFactor": lp.stiffnessFactor if lp is not None else None,
              "steerRatio": lp.steerRatio if lp is not None else None,
              "roll": lp.roll if lp is not None else None,
              "posenetSpeed": lp.posenetSpeed if lp is not None else None,
              "sensorValid": lp.sensorValid if lp is not None else None,
            },
            "livePose": {
              "velocityDevice": {
                "x": pose.velocityDevice.x if pose is not None else None,
                "y": pose.velocityDevice.y if pose is not None else None,
                "z": pose.velocityDevice.z if pose is not None else None,
              },
              "accelerationDevice": {
                "x": pose.accelerationDevice.x if pose is not None else None,
                "y": pose.accelerationDevice.y if pose is not None else None,
                "z": pose.accelerationDevice.z if pose is not None else None,
              },
            },
            "liveTorqueParameters": {
              "latAccelFactorFiltered": ltp.latAccelFactorFiltered if ltp is not None else None,
              "frictionCoefficientFiltered": ltp.frictionCoefficientFiltered if ltp is not None else None,
            },
            "liveDelay": {
              "lateralDelay": ld.lateralDelay if ld is not None else None,
              "status": str(ld.status).split('.')[-1] if ld is not None else None,
            },
            "driverMonitoringState": {
              "awarenessPercent": dms.visionPolicyState.awarenessPercent if dms is not None else None,
              "faceDetected": dms.visionPolicyState.faceDetected if dms is not None else None,
              "isDistracted": dms.visionPolicyState.isDistracted if dms is not None else None,
              "wheelSide": ("right" if dms.isRHD else "left") if dms is not None else None,
              "distractedTypes": [k for k in ('pose', 'eye', 'phone')
                                 if getattr(dms.visionPolicyState.distractedTypes, k)] if dms is not None else None,
              "alertStatus": str(sd2.alertStatus).split('.')[-1] if sd2 is not None else None,
              "alertType": sd2.alertType if sd2 is not None else None,
            },
            "selfdriveState": {
              "enabled": sd2.enabled if sd2 is not None else None,
              "active": sd2.active if sd2 is not None else None,
              "state": str(sd2.state).split('.')[-1] if sd2 is not None else None,
              "experimentalMode": sd2.experimentalMode if sd2 is not None else None,
            },
            "calibration": self._calibration,
            "ego": {
              "speed": cs.vEgo if cs is not None else None,
              "aEgo": cs.aEgo if cs is not None else None,
            },
            "cruise": {
              "setSpeed": cs.vCruise if cs is not None else None,
              "clusterSpeed": cs.vCruiseCluster if cs is not None else None,
            },
          }
        except Exception:
          logger.warning("cockpit data error", exc_info=True)

        try:
          sds = sm['controlsState'].deprecated if sm.seen['controlsState'] else None
          lp2 = sm['longitudinalPlan'] if sm.seen['longitudinalPlan'] else None
          lp_depr = lp2.deprecated if lp2 is not None else None
          radar = sm['radarState'] if sm.seen['radarState'] else None
          lpsp = sm['longitudinalPlanSP'] if sm.seen['longitudinalPlanSP'] else None
          mapsp = sm['liveMapDataSP'] if sm.seen['liveMapDataSP'] else None
          cssp = sm['carStateSP'] if sm.seen['carStateSP'] else None
          sdsps = sm['selfdriveStateSP'] if sm.seen['selfdriveStateSP'] else None

          lead = None
          if radar is not None:
            ld = radar.leadOne
            if ld is not None:
              lead = {"vLead": ld.vLead, "vLeadK": ld.vLeadK, "vRel": ld.vRel, "dRel": ld.dRel}

          plan_sp = None
          if lpsp is not None:
            plan_sp = {"vTarget": lpsp.vTarget}
            if lpsp.smartCruiseControl is not None:
              plan_sp["sccVisionVTarget"] = lpsp.smartCruiseControl.vision.vTarget
              plan_sp["sccMapVTarget"] = lpsp.smartCruiseControl.map.vTarget
            if lpsp.speedLimit is not None:
              plan_sp["speedLimitAssistVTarget"] = lpsp.speedLimit.assist.vTarget

          slr = lpsp.speedLimit.resolver if lpsp is not None and lpsp.speedLimit is not None else None

          icbm_vtarget = None
          if sdsps is not None and sdsps.intelligentCruiseButtonManagement is not None:
            icbm_vtarget = sdsps.intelligentCruiseButtonManagement.vTarget

          self._speed_data = {
            "ego": {
              "speed": sds.vEgo if sds is not None else None,
              "aEgo": sds.aEgo if sds is not None else None,
              "standstill": sds.vEgo < 0.01 if sds is not None else None,
            },
            "cruise": {
              "setSpeed": sds.vCruise if sds is not None else None,
              "clusterSpeed": sds.vCruiseCluster if sds is not None else None,
            },
            "lead": lead,
            "plan": {
              "vTarget": lp_depr.vTarget if lp_depr is not None else None,
              "vCruise": lp_depr.vCruise if lp_depr is not None else None,
              "vMax": lp_depr.vMax if lp_depr is not None else None,
              "vCurvature": lp_depr.vCurvature if lp_depr is not None else None,
              "aTarget": lp2.aTarget if lp2 is not None else None,
            },
            "planSP": plan_sp,
            "limit": {
              "speedLimit": slr.speedLimit if slr is not None else None,
              "speedLimitFinal": slr.speedLimitFinal if slr is not None else None,
              "speedLimitOffset": slr.speedLimitOffset if slr is not None else None,
              "distToSpeedLimit": slr.distToSpeedLimit if slr is not None else None,
              "valid": slr.speedLimitValid if slr is not None else None,
            },
            "map": {
              "speedLimit": mapsp.speedLimit if mapsp is not None else None,
              "valid": mapsp.speedLimitValid if mapsp is not None else None,
              "speedLimitAhead": mapsp.speedLimitAhead if mapsp is not None else None,
              "aheadValid": mapsp.speedLimitAheadValid if mapsp is not None else None,
              "aheadDist": mapsp.speedLimitAheadDistance if mapsp is not None else None,
            },
            "carSpeedLimit": cssp.speedLimit if cssp is not None else None,
            "icbmVtarget": icbm_vtarget,
          }
        except Exception:
          logger.warning("speed data error", exc_info=True)
    except Exception:
      logger.warning("diag loop error", exc_info=True)

  @staticmethod
  def _msgq_readers(name):
    try:
      import struct
      with open(f'/dev/shm/msgq_{name}', 'rb') as f:
        return struct.unpack('<Q', f.read(8))[0]
    except Exception:
      return None
