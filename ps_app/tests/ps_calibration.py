"""Synthetic numerical fixtures only; never a deployable machine calibration."""
import copy
import math
import unittest
from ps_core import run, batch, FIXTURE


def parameters():
    f = copy.deepcopy(FIXTURE['fixture'])
    f.update(id='synthetic_calibration', acceleration_mm_s2=20,max_samples='20000',
             max_sample_distance_mm=.05, max_joint_step_deg=.1,
             pulse_interval_us='63', segment_guard_us='32',
             xy_envelope=dict(center_mm=[0,0],radii_mm=[20,20],margin_mm=1),
             workspace={'min': [-20, -20, -20], 'max': [20, 20, 20]})
    return dict(schema_version=2, id='synthetic_calibration', golden={}, fixture=f,
                calibration=dict(reference_id='synthetic_not_hardware',
                                 encoder_interpretation='signed_turns_plus_u16_fraction',
                                 home_joint_deg=[20, 20, 20],
                                 encoder_home=[dict(carry='0', value=1000)]*3,
                                 encoder_units_per_joint_deg=[819.2]*3,
                                 pl_sign=[1, -1, 1], physical_min_deg=[0]*3,
                                 physical_max_deg=[90]*3, margin_min_deg=[3]*3,
                                 margin_max_deg=[4]*3, tracking_tolerance_deg=.1,
                                 max_age_us='500000', max_skew_us='100000'))


def publication():
    rows = [dict(axis=a, slot=0, valid=True, stale=False,
                 valid_generation='3', valid_revision='2', age_us='10000',
                 last_valid=dict(query=0x30, address=0xe0+a, data_valid=True,
                                 value=dict(carry='0', value=1000),
                                 event_us=str(100000+a*10000), sequence=str(a)))
            for a in range(3)]
    return dict(command_position=dict(valid=True, steps=['0']*3),
                driver_feedback=dict(observed_monotonic_us='200000',
                                     collector_generation='3', revision='2', rows=rows))


class Calibration(unittest.TestCase):
    def test_fk_independent_sphere_residuals_and_golden_roundtrip(self):
        points = [[x, y, z] for x in (-50, 0, 50) for y in (-50, 0, 50)
                  for z in (-160, -200, -250, -300)]
        ik = batch([dict(op='ik', xyz_mm=p) for p in points])
        for p, inverse in zip(points, ik):
            self.assertTrue(inverse['ok'], inverse)
            q = inverse['result']['joint_deg']
            fk = run(dict(op='fk', joint_deg=q))
            self.assertTrue(fk['ok'], (p, fk))
            xyz = fk['result']['xyz_mm']
            self.assertLess(math.dist(xyz, p), .001)
            for angle, nx, ny in zip(q, (0, -math.sqrt(3)/2, math.sqrt(3)/2), (-1, .5, .5)):
                d = 83.7-30.4+150*math.cos(math.radians(angle))
                e = [nx*d, ny*d, -150*math.sin(math.radians(angle))]
                self.assertAlmostEqual(math.dist(xyz, e), 280, places=4)

    def test_home_pose_and_actual_zero(self):
        p = parameters()
        p['fixture']['joint_min_deg'] = [3]*3
        p['fixture']['joint_max_deg'] = [86]*3
        r = run(dict(op='calibration_validate', parameters=p))
        self.assertTrue(r['ok'], r)
        self.assertFalse(r['result']['position_valid'])
        pose = run(dict(op='calibration_pose', parameters=p, publication=publication(), now_us='210000'))
        self.assertTrue(pose['ok'], pose)
        self.assertLess(max(abs(x) for x in pose['result']['xyz_mm']), 1e-10)
        self.assertEqual(pose['result']['source'], 'encoder_0x30_calibrated_fk')

    def test_stale_missing_identity_and_command_mismatch(self):
        for mutate in [lambda t: t['driver_feedback']['rows'].pop(),
                       lambda t: t['driver_feedback']['rows'][0].update(valid_revision='1'),
                       lambda t: t['driver_feedback']['rows'][0].update(age_us='500000'),
                       lambda t: t['command_position'].update(valid=False),
                       lambda t: t['command_position'].update(steps=['1000','0','0']),
                       lambda t: t['driver_feedback']['rows'][0]['last_valid'].update(query=0x33)]:
            t = publication(); mutate(t)
            self.assertFalse(run(dict(op='calibration_pose', parameters=parameters(), publication=t, now_us='210000'))['ok'])

    def test_translation_mapping_boundaries_and_first_segment(self):
        p = parameters();p['fixture'].update(joint_min_deg=[3]*3, joint_max_deg=[86]*3)
        start = dict(valid=True, position_id='measured_synthetic', xyz_mm=[0]*3, steps=['0']*4)
        def planned(origin, target, begin=start):
            return run(dict(op='calibration_plan', parameters=p, start=begin,
                            points=[dict(xyz_mm=target)], work_origin_mm=origin))
        a, b = planned([0]*3, [1,0,0]), planned([10,0,0], [-9,0,0])
        self.assertTrue(a['ok'], a);self.assertTrue(b['ok'], b)
        self.assertEqual([s['steps'] for s in a['result']['samples']], [s['steps'] for s in b['result']['samples']])
        self.assertEqual(a['result']['target']['machine_xyz_mm'], b['result']['target']['machine_xyz_mm'])
        self.assertEqual(planned([10,0,0], [11,0,0])['error']['code'], 'WORKSPACE_RANGE')
        self.assertEqual(planned([0]*3,[18,18,0])['error']['code'],'WORKSPACE_RANGE')
        begin=copy.deepcopy(start);begin['steps']=['500','0','0','0']
        self.assertEqual(planned([0]*3,[1,0,0],begin)['error']['code'], 'PULSE_RATE')

    def test_parameter_fail_closed(self):
        for key,value in [('speed_mm_s',20.01), ('acceleration_mm_s2',20.01), ('pulse_interval_us','62')]:
            p=parameters();p['fixture'].update(joint_min_deg=[3]*3,joint_max_deg=[86]*3);p['fixture'][key]=value
            self.assertFalse(run(dict(op='calibration_validate',parameters=p))['ok'])

    def test_real_jog_profile_and_boundary(self):
        p=parameters();p['fixture'].update(joint_min_deg=[3]*3,joint_max_deg=[86]*3)
        pose=run(dict(op='calibration_pose',parameters=p,publication=publication(),now_us='210000'))['result']
        velocity=0
        for n in range(8):
            r=run(dict(op='calibration_jog',parameters=p,start=pose,axis=0,sign=1,speed_mm_s=5,velocity_mm_s=velocity))
            self.assertTrue(r['ok'],r);out=r['result'];velocity=out['velocity_mm_s'];pose=out['last_pose']
            self.assertAlmostEqual(velocity,min(5,(n+1)),places=8)
            self.assertEqual(sum(int(s['duration_us']) for s in out['samples']),50000)
        self.assertAlmostEqual(pose['xyz_mm'][0],1.375,places=8)
        p['fixture']['workspace']['max'][0]=pose['xyz_mm'][0]+.001
        self.assertEqual(run(dict(op='calibration_jog',parameters=p,start=pose,axis=0,sign=1,speed_mm_s=5,velocity_mm_s=velocity))['error']['code'],'WORKSPACE_RANGE')


if __name__ == '__main__':
    unittest.main()
